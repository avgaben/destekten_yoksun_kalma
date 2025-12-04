from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from models import (
    CalculationInput,
    CalculationResult,
    YearRow,
    DependentType,
    Gender,
)
from life_tables import get_life_expectancy
from income import calculate_monthly_income
from wages import get_min_wage_net
from sharing import base_shares, normalize_shares, parent_names
from sgk import compute_sgk_psd
from ayim import get_marriage_discount_factor

def _validate_input(ci: CalculationInput) -> None:
    """Temel mantıksal kontroller.

    Profesyonel kullanım için, bariz hatalı girdileri erken yakalar.
    """
    if ci.hesap_tarihi < ci.olay_tarihi:
        raise ValueError("Hesap tarihi, olay tarihinden önce olamaz.")

    if ci.destek.birth >= ci.olay_tarihi:
        raise ValueError(
            "Destek doğum tarihi, olay tarihinden sonra "
            "ya da olay tarihiyle aynı olamaz."
        )

    if not (0.0 <= ci.fault_rate <= 100.0):
        raise ValueError("Kusur oranı 0 ile 100 arasında olmalıdır.")

    if ci.report_discount_rate < 0.0:
        raise ValueError("Rapor iskonto oranı negatif olamaz.")

    if ci.technical_interest < 0.0:
        raise ValueError("Teknik faiz oranı negatif olamaz.")


def _age_of(birth: date, ref_date: date) -> float:
    """Yaşı yıl cinsinden (ondalıklı) hesapla."""
    days = (ref_date - birth).days
    return max(0.0, days / 365.25)


def _int_age_on(birth: date, ref: date) -> int:
    """Klasik takvim yaşını (tam yıl) hesaplar."""
    age = ref.year - birth.year
    if (ref.month, ref.day) < (birth.month, birth.day):
        age -= 1
    return age


def _add_years(d: date, years: float) -> date:
    """
    Bir tarihe 'years' kadar yıl ekler (years ondalıklı olabilir).
    """
    int_years = int(years)
    frac_years = years - int_years
    # tam yıl
    try:
        d2 = d.replace(year=d.year + int_years)
    except ValueError:
        d2 = d.replace(month=2, day=28, year=d.year + int_years)
    # kesirli yıl
    extra_days = int(round(frac_years * 365.25))
    return d2 + timedelta(days=extra_days)


def _expected_death_date(birth: date, gender: Gender, ci: CalculationInput) -> date:
    """
    Hesap tarihindeki yaş + bakiye ömür (TRH 2010 / PMF 1931) ile beklenen ölüm tarihini verir.
    """
    age_at_hesap = _age_of(birth, ci.hesap_tarihi)
    le_years = get_life_expectancy(int(age_at_hesap), ci.life_table, gender)
    return _add_years(ci.hesap_tarihi, le_years)


def _overlap_days(start1: date, end1: date, start2: date, end2: date) -> int:
    """
    [start1, end1) ile [start2, end2) aralığının kesişim gün sayısını döndürür.
    end hariç (yarı açık aralık).
    """
    start = max(start1, start2)
    end = min(end1, end2)
    if end <= start:
        return 0
    return (end - start).days


def _yearly_support(ci: CalculationInput, year: int) -> float:
    """
    Destek için o yılın TAMAMI aktif kabul edilse yıllık destek ne olurdu?
    (12 * aylık), aktif/pasif ayrımı + askerlik hariç.
    Sonradan gün oranıyla çarpıyoruz.
    """
    dt = date(year, ci.olay_tarihi.month, ci.olay_tarihi.day)
    age = _age_of(ci.destek.birth, dt)

    # Askerlik süresini tazminat dışı bırak (sadece erkek destek için)
    if ci.military_enabled and ci.destek.gender == Gender.MALE:
        start = ci.military_start_age
        dur_years = ci.military_duration_months / 12.0
        end = start + dur_years
        if start <= age < end:
            return 0.0

    if age < ci.active_start_age:
        return 0.0

    # Aktif dönem
    if age <= ci.active_end_age:
        monthly = calculate_monthly_income(ci, dt)
        return monthly * 12.0

    # PASİF DÖNEM
    if ci.passive_income_type.name == "PASSIVE_MIN_WAGE":
        monthly = get_min_wage_net(dt, use_agi=False)
        return monthly * 12.0

    # Oran modeli
    active_monthly = calculate_monthly_income(ci, dt)
    return active_monthly * 12.0 * ci.passive_ratio


def _period_type(year: int, ci: CalculationInput) -> str:
    """Sadece raporda etiket için."""
    ref_date = date(year, ci.olay_tarihi.month, ci.olay_tarihi.day)
    if ref_date < ci.hesap_tarihi:
        return "Geçmiş"
    age = _age_of(ci.destek.birth, ref_date)
    if age <= ci.active_end_age:
        return "Gelecek Aktif"
    return "Gelecek Pasif"


def compute_support(ci: CalculationInput) -> CalculationResult:
    """
    Tam aktüeryal, tarih bazlı DYKT hesabı.
    """

    INF_DATE = date(9999, 12, 31)

    _validate_input(ci)

    # 1) Destekçinin destek süresi
    supporter_start = ci.olay_tarihi
    supporter_end = _expected_death_date(ci.destek.birth, ci.destek.gender, ci)

    # 2) Bağımlılar için beklenen ölüm ve destek aralıkları
    dep_death_dates: Dict[str, date] = {}
    dep_intervals: Dict[str, Optional[Tuple[date, date]]] = {}
    dep_by_name: Dict[str, object] = {}

    for d in ci.dependents:
        name = d.person.name
        dep_by_name[name] = d

        death_date = _expected_death_date(d.person.birth, d.person.gender, ci)
        dep_death_dates[name] = death_date

        # Başlangıç: olay tarihinden önce destek yok;
        # çocuk doğumu olay tarihinden sonra ise doğum dikkate alınır.
        start = max(ci.olay_tarihi, d.person.birth)

        # Çocuk destek yaşı sınırı
        child_limit = INF_DATE
        if d.dep_type == DependentType.CHILD:
            if d.custom_support_years is not None:
                years = d.custom_support_years
            else:
                if d.is_student:
                    years = ci.child_support_age_student
                elif d.person.gender == Gender.FEMALE:
                    years = ci.child_support_age_female_non_student
                else:
                    years = ci.child_support_age_male
            child_limit = _add_years(d.person.birth, years)

        custom_exit = d.custom_exit_date or INF_DATE

        end = min(death_date, child_limit, custom_exit, supporter_end)

        if end <= start:
            dep_intervals[name] = None
        else:
            dep_intervals[name] = (start, end)

    # 3) Varsayılan eş ve çocuklar (bekâr senaryosu)
    virtual_intervals: Dict[str, Tuple[date, date]] = {}
    virtual_children_birth: Dict[str, date] = {}

    has_real_spouse = any(d.dep_type == DependentType.SPOUSE for d in ci.dependents)
    if ci.assume_marriage_if_single and not has_real_spouse:
        marriage_date = _add_years(ci.destek.birth, ci.assumed_marriage_age)
        if marriage_date < supporter_end:
            vs_start = max(ci.olay_tarihi, marriage_date)
            vs_end = supporter_end
            if vs_end > vs_start:
                virtual_intervals["Varsayılan Eş"] = (vs_start, vs_end)

            # Çocuklar
            child1_birth = _add_years(
                ci.destek.birth,
                ci.assumed_marriage_age + ci.assumed_child1_after_years,
            )
            child2_birth = _add_years(
                ci.destek.birth,
                ci.assumed_marriage_age + ci.assumed_child2_after_years,
            )
            for label, birth in [
                ("Varsayılan Çocuk 1", child1_birth),
                ("Varsayılan Çocuk 2", child2_birth),
            ]:
                end = _add_years(birth, ci.child_support_age_male)
                end = min(end, supporter_end)
                start = max(ci.olay_tarihi, birth)
                if end > start:
                    virtual_intervals[label] = (start, end)
                    virtual_children_birth[label] = birth

    # 4) Temel paylar ve anne-baba havuzu oranı
    base = base_shares(ci)
    parents = parent_names(ci)

    total_base = sum(base.values())
    parent_base_total = sum(base.get(p, 0.0) for p in parents)
    parent_fraction = (
        parent_base_total / total_base
        if (total_base > 0 and parent_base_total > 0)
        else 0.0
    )

    rows: List[YearRow] = []

    # 5) Yıllık bazda (gün oranlı) hesap
    start_year = supporter_start.year
    end_year = supporter_end.year

    for year in range(start_year, end_year + 1):
        year_start = date(year, 1, 1)
        year_end = date(year + 1, 1, 1)
        days_in_year = (year_end - year_start).days

        # Destekçinin o yıl destekte bulunduğu gün sayısı
        supp_days = _overlap_days(supporter_start, supporter_end, year_start, year_end)
        if supp_days <= 0:
            continue

        fraction_supporter = supp_days / days_in_year

        # Yıllık tam destek * gün oranı
        yearly_full = _yearly_support(ci, year)
        if yearly_full <= 0:
            continue

        gross_support = yearly_full * fraction_supporter

        # Rapor iskontosu / teknik faiz
        pv_year = gross_support
        k = year - ci.hesap_tarihi.year
        if k > 0:
            discount_rate = 0.0
            # Progresif yöntemde rapor iskonto oranı kullanılır
            if ci.use_progresif and ci.report_discount_rate > 0:
                discount_rate = ci.report_discount_rate / 100.0
            # Klasik aktüeryal yaklaşıma geçilirse teknik faiz kullanılır
            elif (not ci.use_progresif) and ci.technical_interest > 0:
                discount_rate = ci.technical_interest / 100.0

            if discount_rate > 0.0:
                discount_factor = 1.0 / ((1.0 + discount_rate) ** k)
                pv_year = gross_support * discount_factor

        # 5.a) Anne-baba havuzu (sadece separate_parent_pool=True ise)
        parent_amounts: Dict[str, float] = {}
        parent_total = 0.0

        if ci.separate_parent_pool:
            active_parents = []
            parent_weights: Dict[str, float] = {}

            for p_name in parents:
                interval = dep_intervals.get(p_name)
                if not interval:
                    continue
                ps, pe = interval
                pdays = _overlap_days(ps, pe, year_start, year_end)
                if pdays <= 0:
                    continue
                active_parents.append(p_name)
                parent_weights[p_name] = base.get(p_name, 0.0) * (pdays / days_in_year)

            if active_parents and parent_fraction > 0:
                parent_total = pv_year * parent_fraction

                # Eş veya çocuk (gerçek ya da sanal) aktifse %25 sınırı
                has_spouse_or_child = False

                for d in ci.dependents:
                    if d.dep_type not in (DependentType.SPOUSE, DependentType.CHILD):
                        continue
                    interval = dep_intervals.get(d.person.name)
                    if not interval:
                        continue
                    ds, de = interval
                    if _overlap_days(ds, de, year_start, year_end) > 0:
                        has_spouse_or_child = True
                        break

                if not has_spouse_or_child:
                    for vname, (vs, ve) in virtual_intervals.items():
                        if _overlap_days(vs, ve, year_start, year_end) > 0:
                            has_spouse_or_child = True
                            break

                if ci.parent_share_cap_25_enabled and has_spouse_or_child:
                    max_parent_total = pv_year * 0.25
                    if parent_total > max_parent_total:
                        parent_total = max_parent_total

                # Tek ebeveyn aktifse tüm havuz ona
                if len(active_parents) == 1:
                    parent_amounts[active_parents[0]] = parent_total
                else:
                    wsum = sum(parent_weights.values()) or 1.0
                    for p_name in active_parents:
                        w = parent_weights[p_name]
                        parent_amounts[p_name] = parent_total * (w / wsum)

        non_parent_total = pv_year - parent_total
        if non_parent_total < 0:
            non_parent_total = 0.0

        # 5.b) Non-parent payları (destek + eş + çocuklar + (gerekirse) anne-baba + sanal eş/çocuklar)
        non_parent_weights: Dict[str, float] = {}

        non_parent_weights["destek"] = 2.0 * fraction_supporter

        # Gerçek eş, çocuk ve (separate_parent_pool=False ise) anne-baba
        for d in ci.dependents:
            name = d.person.name
            interval = dep_intervals.get(name)
            if not interval:
                continue
            ds, de = interval
            ddays = _overlap_days(ds, de, year_start, year_end)
            if ddays <= 0:
                continue
            frac = ddays / days_in_year

            if d.dep_type == DependentType.SPOUSE:
                w = 2.0 * frac
            elif d.dep_type == DependentType.CHILD:
                w = 1.0 * frac
            elif (not ci.separate_parent_pool) and d.dep_type in (
                DependentType.MOTHER,
                DependentType.FATHER,
            ):
                base_w = 0.5 if d.reduced_share else 1.0
                w = base_w * frac
            else:
                continue

            non_parent_weights[name] = non_parent_weights.get(name, 0.0) + w

        # Sanal eş ve çocuklar
        for vname, (vs, ve) in virtual_intervals.items():
            ddays = _overlap_days(vs, ve, year_start, year_end)
            if ddays <= 0:
                continue
            frac = ddays / days_in_year
            if vname == "Varsayılan Eş":
                w = 2.0 * frac
            else:
                w = 1.0 * frac
            non_parent_weights[vname] = non_parent_weights.get(vname, 0.0) + w

        non_parent_ratios = normalize_shares(non_parent_weights)
        shares_amount: Dict[str, float] = {}
        for name, ratio in non_parent_ratios.items():
            shares_amount[name] = non_parent_total * ratio

        # 5.b-2) Tek havuz modunda anne-baba toplam payını %25 ile sınırla (isteğe bağlı)
        if (not ci.separate_parent_pool) and ci.parent_share_cap_25_enabled:
            parent_sum = sum(shares_amount.get(p, 0.0) for p in parents)
            other_names = [n for n in shares_amount.keys() if n not in parents]
            others_sum = sum(shares_amount.get(n, 0.0) for n in other_names)
            if parent_sum > 0 and others_sum > 0:
                max_parent_total = pv_year * 0.25
                if parent_sum > max_parent_total + 1e-9:
                    scale_parent = max_parent_total / parent_sum
                    remaining = pv_year - max_parent_total
                    scale_others = remaining / others_sum if others_sum > 0 else 1.0

                    for p in parents:
                        if p in shares_amount:
                            shares_amount[p] *= scale_parent
                    for n in other_names:
                        shares_amount[n] *= scale_others

        # Anne-baba tutarlarını ekle (separate_parent_pool=True ise buradan gelir)
        for p_name, amt in parent_amounts.items():
            shares_amount[p_name] = shares_amount.get(p_name, 0.0) + amt

        # 5.c) AYİM evlenme şansı indirimi
        if ci.apply_ayim:
            under18 = 0
            # Gerçek çocuklar
            for d in ci.dependents:
                if d.dep_type != DependentType.CHILD:
                    continue
                interval = dep_intervals.get(d.person.name)
                if not interval:
                    continue
                ds, de = interval
                if _overlap_days(ds, de, year_start, year_end) <= 0:
                    continue
                mid_date = date(year, 7, 1)
                age = _age_of(d.person.birth, mid_date)
                if age < 18.0:
                    under18 += 1
            # Sanal çocuklar
            for vname, birth in virtual_children_birth.items():
                interval = virtual_intervals.get(vname)
                if not interval:
                    continue
                vs, ve = interval
                if _overlap_days(vs, ve, year_start, year_end) <= 0:
                    continue
                mid_date = date(year, 7, 1)
                age = _age_of(birth, mid_date)
                if age < 18.0:
                    under18 += 1

            # Gerçek eş(ler)
            for d in ci.dependents:
                if d.dep_type != DependentType.SPOUSE or not d.apply_marriage_discount:
                    continue
                interval = dep_intervals.get(d.person.name)
                if not interval:
                    continue
                ds, de = interval
                if _overlap_days(ds, de, year_start, year_end) <= 0:
                    continue
                mid_date = date(year, 7, 1)
                spouse_age = _age_of(d.person.birth, mid_date)
                factor = get_marriage_discount_factor(
                    int(spouse_age), d.person.gender, under18
                )
                amt = shares_amount.get(d.person.name, 0.0)
                shares_amount[d.person.name] = amt * factor

            # Sanal eş
            if "Varsayılan Eş" in virtual_intervals:
                vs, ve = virtual_intervals["Varsayılan Eş"]
                if _overlap_days(vs, ve, year_start, year_end) > 0:
                    mid_date = date(year, 7, 1)
                    spouse_age = _age_of(ci.destek.birth, mid_date)
                    virt_spouse_gender = (
                        Gender.FEMALE if ci.destek.gender == Gender.MALE else Gender.MALE
                    )
                    factor = get_marriage_discount_factor(
                        int(spouse_age), virt_spouse_gender, under18
                    )
                    amt = shares_amount.get("Varsayılan Eş", 0.0)
                    shares_amount["Varsayılan Eş"] = amt * factor

        ref_date = date(year, ci.olay_tarihi.month, ci.olay_tarihi.day)
        age_supporter = _int_age_on(ci.destek.birth, ref_date)
        period_type = _period_type(year, ci)

        row = YearRow(
            year=year,
            age_supporter=age_supporter,
            period_type=period_type,
            gross_support=gross_support,
            present_value=pv_year,
            shares=shares_amount,
        )
        rows.append(row)

    # 6) Toplamlar
    total_support = float(sum(r.present_value for r in rows))
    total_by_person: Dict[str, float] = {}
    for r in rows:
        for name, val in r.shares.items():
            total_by_person[name] = total_by_person.get(name, 0.0) + val

    # SGK PSD
    psd = compute_sgk_psd(ci)
    total_after_sgk = total_support
    if ci.sgk_deduction_type != ci.sgk_deduction_type.NONE:
        if ci.sgk_deduction_type == ci.sgk_deduction_type.HALF:
            total_after_sgk = total_support - psd * 0.5
        else:
            total_after_sgk = total_support - psd
    # Negatif tazminat oluşmaması için alt sınır
    if total_after_sgk < 0.0:
        total_after_sgk = 0.0

    # Yetiştirme gideri
    training_total = 0.0
    age_at_olay = _age_of(ci.destek.birth, ci.olay_tarihi)
    if ci.training_enabled and age_at_olay < 18.0:
        yil_sayisi = 18.0 - age_at_olay
        if ci.training_base_monthly > 0:
            base_monthly = ci.training_base_monthly
        else:
            base_monthly = get_min_wage_net(ci.olay_tarihi, use_agi=False)

        father_name = None
        mother_name = None
        for d in ci.dependents:
            if d.dep_type == DependentType.FATHER:
                father_name = d.person.name
            if d.dep_type == DependentType.MOTHER:
                mother_name = d.person.name

        if ci.father_working and father_name:
            t_father = base_monthly * 12.0 * ci.training_rate * yil_sayisi
            training_total += t_father
            total_by_person[father_name] = total_by_person.get(father_name, 0.0) - t_father

        if ci.mother_working and mother_name:
            t_mother = base_monthly * 12.0 * ci.training_rate * yil_sayisi
            training_total += t_mother
            total_by_person[mother_name] = total_by_person.get(mother_name, 0.0) - t_mother

        total_support -= training_total
        total_after_sgk -= training_total

    # Kusur indirimi
    total_after_fault = total_after_sgk * (1.0 - ci.fault_rate / 100.0)

    return CalculationResult(
        rows=rows,
        total_support=total_support,
        total_by_person=total_by_person,
        sgk_psd_deduction=psd,
        total_after_sgk=total_after_sgk,
        total_after_fault=total_after_fault,
        training_total=training_total,
        supporter_start=supporter_start,
        supporter_end=supporter_end,
        dependent_intervals=dep_intervals,
        virtual_intervals=virtual_intervals,
    )

