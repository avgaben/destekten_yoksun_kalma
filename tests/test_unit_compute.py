import datetime
from models import (
    CalculationInput,
    Person,
    Gender,
    LifeTableType,
    IncomeMode,
)
from calculator import compute_support

def make_base_ci() -> CalculationInput:
    destek = Person(name="Maktul", birth=datetime.date(1985, 1, 1), gender=Gender.MALE)
    ci = CalculationInput(
        olay_tarihi=datetime.date(2020, 1, 1),
        hesap_tarihi=datetime.date(2025, 1, 1),
        destek=destek,
        income_mode=IncomeMode.MANUAL,
    )
    # Temel gelir bilgisi
    ci.monthly_income = 50000.0 / 12.0  # yıllık 50k TL örneği
    ci.regular_extra_income = 0.0

    # Yaşam tablosu ve dönemler
    ci.life_table = LifeTableType.PMF1931
    ci.active_start_age = 18
    ci.active_end_age = 60

    # Default parametreler (gerekirse burada override edilebilir)
    ci.passive_ratio = 0.7
    ci.report_discount_rate = 0.03

    return ci

def test_compute_returns_result_shape_and_types():
    ci = make_base_ci()
    res = compute_support(ci)
    assert hasattr(res, "total_support"), "Result should have total_support"
    assert isinstance(res.total_support, float), "total_support should be float"
    assert hasattr(res, "rows"), "Result should have rows list"
    assert isinstance(res.rows, list)

def test_deterministic_same_input_runs_equal():
    ci = make_base_ci()
    r1 = compute_support(ci)
    r2 = compute_support(ci)
    # Tam eşitlik beklenir; eğer içerde rastgelelik varsa bu test başarısız olur
    assert r1.total_support == r2.total_support, "Aynı girişle farklı toplam destek oldu"

def test_parameter_change_affects_output():
    ci_base = make_base_ci()
    res_base = compute_support(ci_base)

    # Pasif oranı değiştir
    ci_mod = make_base_ci()
    ci_mod.passive_ratio = 0.4  # daha düşük pasif gelir oranı => genelde toplam destek değişir
    res_mod = compute_support(ci_mod)

    assert res_base.total_support != res_mod.total_support, "Passive ratio değiştirilince total_support değişmeli"

def test_discount_rate_monotonicity():
    ci_low = make_base_ci()
    ci_low.report_discount_rate = 0.0
    res_low = compute_support(ci_low)

    ci_high = make_base_ci()
    ci_high.report_discount_rate = 0.10
    res_high = compute_support(ci_high)

    # Yüksek iskonto oranı nominalde bugünkü değeri düşürmelidir
    assert res_high.total_support <= res_low.total_support + 1e-6