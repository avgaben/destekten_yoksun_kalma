# full_report.py
from __future__ import annotations

from datetime import date
from typing import List

import pandas as pd

from models import (
    CalculationInput,
    CalculationResult,
    IncomeMode,
    LifeTableType,
    PassiveIncomeType,
    ProfileType,
    Gender,
)
from legal_loader import LegalRepository
from report_text import build_legal_explanation_text
from reference_text import build_parameter_explanation


def _format_date_tr(d: date | None) -> str:
    if not d:
        return "-"
    return d.strftime("%d.%m.%Y")


def _format_money(v: float | int | None) -> str:
    if v is None:
        v = 0.0
    # 1234567.89 -> 1.234.567,89
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " TL"


def _gender_str(g: Gender) -> str:
    return "Erkek" if g == Gender.MALE else "Kadın"


def _life_table_str(lt: LifeTableType) -> str:
    if lt == LifeTableType.TRH2010:
        return "TRH 2010 Yaşam Tablosu"
    if lt == LifeTableType.PMF1931:
        return "PMF 1931 Yaşam Tablosu"
    return str(lt.value)


def _income_mode_str(mode: IncomeMode) -> str:
    if mode == IncomeMode.ASGARI:
        return "Asgari Ücret Esaslı"
    if mode == IncomeMode.MANUAL:
        return "Beyan Edilen Net Gelir Esaslı"
    return str(mode.value)


def _passive_type_str(pt: PassiveIncomeType, ratio: float) -> str:
    if pt == PassiveIncomeType.PASSIVE_MIN_WAGE:
        return "Pasif dönemde AGİ'siz net asgari ücret esas alınmıştır."
    if pt == PassiveIncomeType.PASSIVE_RATIO:
        return f"Pasif dönemde aktif gelirin %{int(ratio * 100)}'i oranında gelir kabul edilmiştir."
    return str(pt.value)


def _profile_str(p: ProfileType) -> str:
    if p == ProfileType.YARGITAY:
        return "Yargıtay Modu (içtihatlara ağırlık veren varsayımlar)"
    if p == ProfileType.EXPERT:
        return "Bilirkişi Esnek Modu (bilirkişinin tespit ve takdirine göre ayarlanabilir parametreler)"
    return str(p.value)


def _build_olay_bilgileri(ci: CalculationInput) -> str:
    destek_age_at_event_years = (ci.olay_tarihi - ci.destek.birth).days / 365.25

    lines: List[str] = []
    lines.append("I. OLAY VE TARAF BİLGİLERİ\n")
    lines.append(f"Olay tarihi: {_format_date_tr(ci.olay_tarihi)}")
    lines.append(f"Hesap tarihi: {_format_date_tr(ci.hesap_tarihi)}\n")

    lines.append("Destek (kazalı):")
    lines.append(f"  Adı soyadı  : {ci.destek.name}")
    lines.append(f"  Doğum tarihi: {_format_date_tr(ci.destek.birth)}")
    lines.append(f"  Cinsiyeti   : {_gender_str(ci.destek.gender)}")
    lines.append(f"  Olay tarihindeki yaşı (yaklaşık): {destek_age_at_event_years:.2f} yıl\n")

    if ci.dependents:
        lines.append("Destekten yoksun kalanlar (hak sahipleri):")
        for d in ci.dependents:
            rel = d.dep_type.value  # "Eş", "Çocuk" vb.
            lines.append(
                f"  - {d.person.name} ({rel}), doğum tarihi: {_format_date_tr(d.person.birth)}, "
                f"cinsiyet: {_gender_str(d.person.gender)}"
            )
        lines.append("")
    else:
        lines.append("Destekten yoksun kalan hak sahibi bulunmamaktadır.\n")

    return "\n".join(lines).strip()


def _build_hesaplama_parametreleri(ci: CalculationInput) -> str:
    lines: List[str] = []
    lines.append("III. HESAPLAMA PARAMETRELERİ VE YÖNTEMİ\n")

    # Yaşam tablosu ve profil
    lines.append(f"Kullanılan yaşam tablosu: {_life_table_str(ci.life_table)}.")
    lines.append(f"Hesaplama profili      : {_profile_str(ci.profile)}\n")

    # Gelir
    lines.append("Gelir esasları:")
    lines.append(f"  - Gelir türü              : {_income_mode_str(ci.income_mode)}")
    if ci.income_mode == IncomeMode.MANUAL:
        lines.append(f"  - Beyan edilen aylık net gelir : {_format_money(ci.monthly_income)}")
        if getattr(ci, 'regular_extra_income', 0.0) > 0:
            lines.append(f"  - Düzenli ek gelir             : {_format_money(ci.regular_extra_income)}")
    else:
        lines.append("  - Gelir, dönemin yürürlükteki asgari ücreti ve AGİ/istisna hükümleri dikkate alınarak belirlenmiştir.")
    lines.append("")

    # Aktif / pasif
    lines.append("Aktif ve pasif dönem parametreleri:")
    lines.append(f"  - Aktif dönem yaş aralığı : {ci.active_start_age} - {ci.active_end_age}")
    lines.append(f"  - Pasif gelir modeli      : {_passive_type_str(ci.passive_income_type, ci.passive_ratio)}")
    lines.append("")

    # Çocuk destek yaşları
    lines.append("Çocuklar için varsayılan destek yaşları:")
    lines.append(f"  - Erkek çocuk (öğrenci değil) : {ci.child_support_age_male} yaşına kadar")
    lines.append(f"  - Kız çocuk (öğrenci değil)   : {ci.child_support_age_female_non_student} yaşına kadar")
    lines.append(f"  - Öğrenci çocuk               : {ci.child_support_age_student} yaşına kadar")
    lines.append("")

    # SGK
    if ci.sgk_monthly_income > 0:
        lines.append("SGK yönünden:")
        lines.append(f"  - Kurumca bağlanan aylık gelir (hesaba esas): {_format_money(ci.sgk_monthly_income)}")
        lines.append(f"  - Peşin sermaye değeri katsayısı           : {ci.sgk_psd_factor}")
        lines.append(f"  - İndirim türü                             : {ci.sgk_deduction_type.value}")
        lines.append("")
    else:
        lines.append("SGK tarafından bağlanan aylık gelir bulunmadığı varsayılmıştır.")
        lines.append("")

    # Kusur ve iskonto
    if ci.fault_rate > 0:
        lines.append(f"Kusur oranı: %{ci.fault_rate:.2f} olup, hesaplanan zarar bu oran nispetinde indirilmiştir.")
    else:
        lines.append("Kusur indirimi uygulanmamıştır.")
    if ci.report_discount_rate > 0:
        lines.append(
            f"Hesap tarihinden sonraki yıllara ait tutarlar için rapor iskontosu olarak %{ci.report_discount_rate:.2f} oranı uygulanmıştır."
        )
    else:
        lines.append("Rapor iskontosu uygulanmamıştır.")
    lines.append("")

    # Askerlik
    if getattr(ci, "military_enabled", False) and ci.destek.gender == Gender.MALE:
        lines.append(
            f"Askerlik hizmeti için, {ci.military_start_age} yaşından itibaren "
            f"{ci.military_duration_months} ay süreyle kazanç elde edilmeyeceği varsayılmış ve bu dönem tazminat dışında bırakılmıştır."
        )
        lines.append("")

    # Yetiştirme gideri
    if getattr(ci, "training_enabled", False):
        oran = getattr(ci, "training_rate", 0.05) * 100
        lines.append(
            f"Kazalının reşit olmaması nedeniyle anne/baba yönünden yetiştirme gideri indirimi uygulanmıştır "
            f"(oran: %{oran:.2f})."
        )
        if getattr(ci, "training_base_monthly", 0.0) > 0:
            lines.append(
                f"Yetiştirme giderine esas aylık gelir, user tarafından belirtilen {_format_money(ci.training_base_monthly)} olarak alınmıştır."
            )
        else:
            lines.append("Yetiştirme giderine esas aylık gelir, olay tarihindeki net asgari ücret üzerinden belirlenmiştir.")
        lines.append("")

    # Anne-baba payları
    if getattr(ci, "separate_parent_pool", False):
        lines.append(
            "Anne ve baba yönünden, eş ve çocuklardan ayrı bir destek havuzu kabul edilmiş; çocuklardan birinin destekten çıkması halinde "
            "payı eş ve diğer çocuklara aktarılmış, anne ve babanın payına eklenmemiştir."
        )
    if getattr(ci, "parent_share_cap_25_enabled", False):
        lines.append(
            "Anne ve babaya bağlanacak gelir bakımından, 5510 sayılı Kanun'un 34. maddesindeki düzenlemeye paralel olarak, "
            "anne-babaya isabet eden pay toplamı kazalının gelirinin %25'i ile sınırlandırılmıştır."
        )
    if not getattr(ci, "separate_parent_pool", False) and not getattr(ci, "parent_share_cap_25_enabled", False):
        lines.append("Anne-baba payları bakımından özel bir sınırlandırma veya ayrı havuz uygulaması yapılmamıştır.")
    lines.append("")

    # Bekar senaryosu
    if getattr(ci, "assume_marriage_if_single", False):
        lines.append(
            "Destek kişinin bekar olması halinde, Yargıtay ve doktrinde kabul gören varsayımlar doğrultusunda, "
            f"{ci.assumed_marriage_age} yaşında evleneceği, evlilikten {ci.assumed_child1_after_years} yıl sonra ilk, "
            f"{ci.assumed_child2_after_years} yıl sonra ikinci çocuğun olacağı kabul edilmiştir."
        )
    else:
        lines.append("Destek kişinin medeni hali bakımından ek bir varsayımsal evlilik/çocuk senaryosu uygulanmamıştır.")

    return "\n".join(lines).strip()


def _build_hesaplama_ozeti(ci: CalculationInput, res: CalculationResult,
                           df_summary: pd.DataFrame, df_phases: pd.DataFrame) -> str:
    lines: List[str] = []
    lines.append("IV. HESAPLAMA ÖZETİ VE TABLOLAR\n")

    # Destek dönemleri (df_phases)
    if not df_phases.empty:
        lines.append("Destek süresine ilişkin dönemsel özet:")
        for _, row in df_phases.iterrows():
            ad = row.get("Dönem", "")
            s = row.get("Başlangıç", None)
            e = row.get("Bitiş", None)
            y = int(row.get("Süre (Yıl)", 0))
            m = int(row.get("Süre (Ay)", 0))
            g = int(row.get("Süre (Gün Kalan)", 0))
            lines.append(
                f"  - {ad}: {_format_date_tr(s)} - {_format_date_tr(e)} "
                f"({y} yıl {m} ay {g} gün)"
            )
        lines.append("")

    # Hak sahipleri (df_summary)
    if not df_summary.empty:
        lines.append("Hak sahipleri bazında destek süresi ve tutar özeti (ayrıntılı tablo: Ek-2):")
        for _, row in df_summary.iterrows():
            name = row.get("Hak Sahibi", "")
            tutar = float(row.get("Toplam Destek Tutarı (TL)", 0.0))
            y = int(row.get("Toplam Destek Süresi (Yıl)", 0))
            m = int(row.get("Toplam Destek Süresi (Ay)", 0))
            g = int(row.get("Toplam Destek Süresi (Gün Kalan)", 0))
            lines.append(
                f"  - {name}: {_format_money(tutar)} "
                f"({y} yıl {m} ay {g} gün destek süresi)"
            )
        lines.append("")

    # Toplamlar
    lines.append(f"Hesaplanan toplam destek zararı (SGK ve kusur indirimi öncesi, yetiştirme gideri dahil): {_format_money(res.total_support)}")
    lines.append(f"Yetiştirme gideri toplamı                                          : {_format_money(res.training_total)}")
    lines.append(f"SGK peşin sermaye değeri indirimi sonrası toplam                   : {_format_money(res.total_after_sgk)}")
    lines.append(f"Kusur indirimi dikkate alındıktan sonraki nihai tazminat tutarı     : {_format_money(res.total_after_fault)}")
    lines.append("")

    lines.append(
        "Ayrıntılı yıllık hesaplamalar, destek süresi ve pay dağılımı Ek-1, Ek-2 ve Ek-3 tablolarında gösterilmiştir."
    )

    return "\n".join(lines).strip()


def _build_sonuc(ci: CalculationInput, res: CalculationResult, df_summary: pd.DataFrame) -> str:
    lines: List[str] = []
    lines.append("V. SONUÇ VE KANAAT\n")

    lines.append(
        "Yukarıda açıklanan hukuki ve teknik esaslar ile yapılan aktüeryal hesaplama sonucunda, "
        "destekten yoksun kalma zararı aşağıdaki şekilde belirlenmiştir."
    )
    lines.append("")

    # Hak sahipleri için brüt tutar özetleri
    if not df_summary.empty:
        lines.append("Hak sahipleri bazında tespit edilen (kusur ve SGK indirimi öncesi) destek tutarları:")
        for _, row in df_summary.iterrows():
            name = row.get("Hak Sahibi", "")
            tutar = float(row.get("Toplam Destek Tutarı (TL)", 0.0))
            lines.append(f"  - {name}: {_format_money(tutar)}")
        lines.append("")

    lines.append(
        f"Toplam destek zararı üzerinden SGK peşin sermaye değeri indirimi ve kusur oranı dikkate alındığında, "
        f"nihai tazminat tutarı {_format_money(res.total_after_fault)} olarak hesaplanmıştır."
    )
    lines.append("")
    lines.append(
        "Mahkemenizin takdir ve taksim yetkisi saklı kalmak kaydıyla, yukarıda belirtilen esas ve hesaplamalar "
        "çerçevesinde hüküm kurulmasının uygun olacağı kanaat ve sonucuna varılmıştır."
    )

    return "\n".join(lines).strip()


def build_full_report(
    ci: CalculationInput,
    res: CalculationResult,
    repo: LegalRepository,
    df_years: pd.DataFrame,
    df_summary: pd.DataFrame,
    df_phases: pd.DataFrame,
) -> str:
    """
    Tam bilirkişi raporu gövdesini üretir.

    Bölümler:
      I. Olay ve Taraf Bilgileri
      II. Hukuki ve Teknik Esaslar
      III. Hesaplama Parametreleri ve Yöntemi
          - Parametrelerin teknik özeti
          - Parametrelere ilişkin hukuki/aktüeryal açıklamalar (reference_text.build_parameter_explanation)
      IV. Hesaplama Özeti ve Tablolar
      V. Sonuç ve Kanaat
    """
    parts: List[str] = []

    # I. Olay ve Taraf Bilgileri
    parts.append(_build_olay_bilgileri(ci))
    parts.append("")

    # II. Hukuki ve Teknik Esaslar (legal_loader + report_text)
    legal_text = build_legal_explanation_text(ci, res, repo)
    if legal_text:
        parts.append("II. HUKUKİ VE TEKNİK ESASLAR\n")
        parts.append(legal_text.strip())
    else:
        parts.append("II. HUKUKİ VE TEKNİK ESASLAR\n")
        parts.append("Hukuki metin veri tabanında kayıtlı açıklama bulunamamıştır.")
    parts.append("")

    # III. Hesaplama Parametreleri ve Yöntemi
    #
    # 1) Teknik özet (mevcut ayrıntılı madde madde yapı)
    section3_technical = _build_hesaplama_parametreleri(ci)
    if section3_technical:
        parts.append(section3_technical.strip())
    else:
        # Emniyet için en az başlığı yazalım
        parts.append("III. HESAPLAMA PARAMETRELERİ VE YÖNTEMİ\n")

    # 2) Parametrelere ilişkin hukuki ve aktüeryal açıklamalar (reference_text.py)
    param_expl = build_parameter_explanation(ci)
    if param_expl:
        parts.append("")  # Bir satır boşluk
        parts.append(
            "Hesaplamada kullanılan parametrelerin hukuki ve aktüeryal esasları aşağıda özetlenmiştir:\n"
        )
        parts.append(param_expl.strip())

    parts.append("")

    # IV. Hesaplama Özeti ve Tablolar
    parts.append(_build_hesaplama_ozeti(ci, res, df_summary, df_phases))
    parts.append("")

    # V. Sonuç ve kanaat
    parts.append(_build_sonuc(ci, res, df_summary))

    # Tek metin
    return "\n\n".join(p.strip() for p in parts if p is not None and str(p).strip()).strip()
