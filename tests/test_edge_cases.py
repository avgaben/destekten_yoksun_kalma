import datetime
from models import CalculationInput, Person, Gender, IncomeMode
from calculator import compute_support

def test_zero_income_handled_gracefully():
    destek = Person(name="Maktul", birth=datetime.date(1985,1,1), gender=Gender.MALE)
    ci = CalculationInput(
        olay_tarihi=datetime.date(2020,1,1),
        hesap_tarihi=datetime.date(2025,1,1),
        destek=destek,
        income_mode=IncomeMode.MANUAL,
    )
    ci.monthly_income = 0.0
    res = compute_support(ci)
    assert hasattr(res, "total_support")
    assert isinstance(res.total_support, float)

def test_high_fault_rate_reduces_total():
    from copy import deepcopy
    ci = CalculationInput(
        olay_tarihi=datetime.date(2020,1,1),
        hesap_tarihi=datetime.date(2025,1,1),
        destek=Person("Maktul", datetime.date(1985,1,1), Gender.MALE),
        income_mode=IncomeMode.MANUAL,
    )
    ci.monthly_income = 4000.0
    ci.fault_rate = 0.0
    r0 = compute_support(ci)

    ci2 = deepcopy(ci)
    ci2.fault_rate = 0.5  # %50 kusur
    r50 = compute_support(ci2)

    assert r50.total_support <= r0.total_support + 1e-6