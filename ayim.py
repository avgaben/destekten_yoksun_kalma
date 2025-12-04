from __future__ import annotations

from models import Gender


def _ayim_base_rate(age: int, gender: Gender) -> float:
    """
    AYİM evlenme şansı yüzdesi (çocuksuz oranlar).
    Kadın ve erkek için ayrı tablolar.
    """
    if gender == Gender.FEMALE:
        if 17 <= age <= 20:
            return 52.0
        if 21 <= age <= 25:
            return 40.0
        if 26 <= age <= 30:
            return 27.0
        if 31 <= age <= 35:
            return 17.0
        if 36 <= age <= 40:
            return 9.0
        if 41 <= age <= 50:
            return 2.0
        if 51 <= age <= 55:
            return 1.0
        return 0.0
    else:
        if 17 <= age <= 20:
            return 90.0
        if 21 <= age <= 25:
            return 70.0
        if 26 <= age <= 30:
            return 48.0
        if 31 <= age <= 35:
            return 30.0
        if 36 <= age <= 40:
            return 15.0
        if 41 <= age <= 50:
            return 4.0
        if 51 <= age <= 55:
            return 2.0
        return 0.0


def get_marriage_discount_factor(age: int, gender: Gender, child_under18_count: int) -> float:
    """
    Evlenme şansı indirimi faktörü:
      - Temel oran: AYİM tablosundan
      - 18 yaş altı her çocuk için %5 azalma
      - İndirim oranı = max(0, temel_oran - 5*çocuk_sayısı)
      - Faktör = 1 - (oran / 100)
    """
    base = _ayim_base_rate(age, gender)
    adj = base - 5.0 * child_under18_count
    if adj < 0.0:
        adj = 0.0
    factor = 1.0 - adj / 100.0
    return factor
