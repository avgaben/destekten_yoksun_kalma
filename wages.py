from __future__ import annotations

from datetime import date
from typing import Dict, List


# Brüt asgari ücret dönemleri (örnekler + yakın dönem)
MIN_WAGE_PERIODS: List[Dict] = [
    {"start": date(2016, 1, 1), "end": date(2017, 1, 1), "gross_monthly": 1647.00},
    {"start": date(2017, 1, 1), "end": date(2018, 1, 1), "gross_monthly": 1777.50},
    {"start": date(2018, 1, 1), "end": date(2019, 1, 1), "gross_monthly": 2029.50},
    {"start": date(2019, 1, 1), "end": date(2020, 1, 1), "gross_monthly": 2558.40},
    {"start": date(2020, 1, 1), "end": date(2021, 1, 1), "gross_monthly": 2943.00},
    {"start": date(2021, 1, 1), "end": date(2022, 1, 1), "gross_monthly": 3577.50},
    {"start": date(2022, 1, 1), "end": date(2022, 7, 1), "gross_monthly": 5004.00},
    {"start": date(2022, 7, 1), "end": date(2023, 1, 1), "gross_monthly": 6471.00},
    {"start": date(2023, 1, 1), "end": date(2023, 7, 1), "gross_monthly": 10008.00},
    {"start": date(2023, 7, 1), "end": date(2024, 1, 1), "gross_monthly": 13414.50},
    {"start": date(2024, 1, 1), "end": date(2025, 1, 1), "gross_monthly": 20002.50},
    {"start": date(2025, 1, 1), "end": date(2100, 1, 1), "gross_monthly": 26005.50},
]


def get_min_wage_gross(dt: date) -> float:
    for p in MIN_WAGE_PERIODS:
        if p["start"] <= dt < p["end"]:
            return p["gross_monthly"]
    return MIN_WAGE_PERIODS[-1]["gross_monthly"]


def compute_agi(dt: date, married: bool, spouse_has_income: bool, child_count: int) -> float:
    """
    AGİ formülü (özet):
      - Çalışan için %50
      - Geliri olmayan eş için +%10
      - 1. ve 2. çocuk için +%7.5
      - 3. çocuk için +%10
      - 4 ve 5. çocuk için +%5

    AGİ = (brüt asgari * toplam_oran * %15) / 12

    2022'den itibaren AGİ kaldırıldığı için 0 döner.
    """
    year = dt.year
    if year < 2008 or year >= 2022:
        return 0.0

    brut = get_min_wage_gross(dt)
    oran = 0.50  # çalışan

    if married and not spouse_has_income:
        oran += 0.10

    if child_count >= 1:
        oran += 0.075
    if child_count >= 2:
        oran += 0.075
    if child_count >= 3:
        oran += 0.10
    if child_count >= 4:
        oran += 0.05
    if child_count >= 5:
        oran += 0.05

    agi_yillik = brut * oran * 0.15
    agi_aylik = agi_yillik / 12.0
    return round(agi_aylik, 2)


def get_min_wage_net(
    dt: date,
    use_agi: bool,
    married: bool = False,
    spouse_has_income: bool = False,
    child_count: int = 0,
) -> float:
    """
    Verilen tarihteki NET asgari ücreti döndürür.

    - 2008–2021:
        * SGK işçi: %14
        * İşsizlik işçi: %1
        * GV: %15
        * Damga vergisi: ~%0.759
        * AGİ: aile durumuna göre
    - 2022+:
        * AGİ kaldırıldı
        * Brüt asgari ücrete denk gelen kısım GV ve DV'den muaf: net = brüt - SGK - işsizlik
    """
    year = dt.year
    brut = get_min_wage_gross(dt)

    # SGK + işsizlik
    sgk_emp = brut * 0.14
    ui_emp = brut * 0.01
    vergi_matrah = brut - sgk_emp - ui_emp

    if year >= 2022:
        net = brut - sgk_emp - ui_emp
        return round(net, 2)

    gv_rate = 0.15
    dv_rate = 0.00759

    gelir_vergisi = vergi_matrah * gv_rate
    damga = brut * dv_rate

    agi = 0.0
    if use_agi:
        agi = compute_agi(dt, married, spouse_has_income, child_count)

    odenen_gv = max(0.0, gelir_vergisi - agi)
    net = brut - sgk_emp - ui_emp - odenen_gv - damga
    return round(net, 2)
