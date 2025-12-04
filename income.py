from __future__ import annotations

from datetime import date

from models import CalculationInput, IncomeMode, DependentType
from wages import get_min_wage_net


def _family_status_for_agi(ci: CalculationInput, dt: date):
    """AGİ için evlilik ve çocuk sayısını belirle."""
    year = dt.year
    # O yıl için mevcut eş var mı?
    spouse_exists = any(d.dep_type == DependentType.SPOUSE for d in ci.dependents)
    spouse_has_income = False
    for d in ci.dependents:
        if d.dep_type == DependentType.SPOUSE:
            spouse_has_income = d.has_income

    # Eğer gerçek eş yok ve varsayılan evlilik senaryosu açıksa:
    age = (dt - ci.destek.birth).days / 365.25
    if not spouse_exists and ci.assume_marriage_if_single and age >= ci.assumed_marriage_age:
        spouse_exists = True
        spouse_has_income = ci.assumed_spouse_has_income

    # Çocuk sayısı: gerçek + varsayılan (18 yaş altı)
    child_count = 0
    for d in ci.dependents:
        if d.dep_type == DependentType.CHILD:
            ca = (dt - d.person.birth).days / 365.25
            if ca < 18:
                child_count += 1

    if ci.assume_marriage_if_single:
        # 1. çocuk
        child1_age = age - (ci.assumed_marriage_age + ci.assumed_child1_after_years)
        if 0 <= child1_age < 18:
            child_count += 1
        # 2. çocuk
        child2_age = age - (ci.assumed_marriage_age + ci.assumed_child2_after_years)
        if 0 <= child2_age < 18:
            child_count += 1

    return spouse_exists, spouse_has_income, child_count


def calculate_monthly_income(ci: CalculationInput, dt: date) -> float:
    """
    Destek için ilgili tarihteki aylık net gelir.
    - Asgari ücretten: get_min_wage_net (AGİ aile durumuna göre)
    - Manuel: kullanıcının net aylığı + Düzenli Ek Gelir
    """
    if ci.income_mode == IncomeMode.ASGARI:
        spouse_exists, spouse_has_income, child_count = _family_status_for_agi(ci, dt)
        return get_min_wage_net(
            dt,
            use_agi=ci.agi_use_family_status,
            married=spouse_exists,
            spouse_has_income=spouse_has_income,
            child_count=child_count,
        )

    return ci.monthly_income + ci.regular_extra_income
