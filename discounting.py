# discounting.py
from __future__ import annotations


def pv_progresif(last_year_income: float, n_years: float) -> float:
    """
    Progresif rant: her yıl %10 artış, %10 iskonto => g = r olduğu için
    bilinen son yıllık gelir * yıl sayısı.
    """
    return last_year_income * n_years


def pv_actuarial(last_year_income: float, n_years: float, technical_interest: float) -> float:
    """
    Devre başı ödemeli belirli süreli rant (äx:n) sadeleştirilmiş hali:
    PV = last_year_income * a-angle-n-i
    a-angle-n-i = (1 - (1+i)^-n) / i
    """
    i = technical_interest / 100.0
    if i <= 0:
        return last_year_income * n_years
    return last_year_income * ((1.0 - (1.0 / ((1.0 + i) ** n_years))) / i)
