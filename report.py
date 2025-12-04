from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from models import CalculationInput, CalculationResult
from calculator import _add_years


def _interval_to_days(start: date, end: date) -> int:
    if end <= start:
        return 0
    return (end - start).days


def _interval_to_ymd(start: date, end: date) -> Tuple[int, int, int]:
    """
    [start, end) aralığını Yıl/Ay/Gün formatına çevir.
    end-1 dahil kabul ediyoruz.
    """
    if end <= start:
        return 0, 0, 0

    end_eff = end - timedelta(days=1)
    y = end_eff.year - start.year
    m = end_eff.month - start.month
    d = end_eff.day - start.day

    if d < 0:
        prev_month_last = end_eff.replace(day=1) - timedelta(days=1)
        d += prev_month_last.day
        m -= 1

    if m < 0:
        m += 12
        y -= 1

    if y < 0:
        return 0, 0, 0

    return y, m, d


def build_yearly_dataframe(res: CalculationResult) -> pd.DataFrame:
    names = set()
    for r in res.rows:
        for n in r.shares.keys():
            names.add(n)

    cols = ["Yıl", "Destek Yaşı", "Dönem", "Yıllık Destek", "Bugünkü Değer"]
    cols.extend(sorted(names))

    data = []
    for r in res.rows:
        row = {
            "Yıl": r.year,
            "Destek Yaşı": r.age_supporter,
            "Dönem": r.period_type,
            "Yıllık Destek": r.gross_support,
            "Bugünkü Değer": r.present_value,
        }
        for n in names:
            row[n] = r.shares.get(n, 0.0)
        data.append(row)

    df = pd.DataFrame(data, columns=cols)
    return df


def build_summary_dataframe(ci: CalculationInput, res: CalculationResult) -> pd.DataFrame:
    records = []

    def display_name(name: str) -> str:
        if name == "destek":
            return ci.destek.name
        return name

    def get_interval_for(name: str) -> Optional[Tuple[date, date]]:
        if name == "destek":
            return res.supporter_start, res.supporter_end
        if name in res.dependent_intervals and res.dependent_intervals[name] is not None:
            return res.dependent_intervals[name]
        if name in res.virtual_intervals:
            return res.virtual_intervals[name]
        return None

    for name, amount in res.total_by_person.items():
        interval = get_interval_for(name)
        if interval is None:
            days = 0
            y = m = d = 0
        else:
            s, e = interval
            days = _interval_to_days(s, e)
            y, m, d = _interval_to_ymd(s, e)

        records.append(
            {
                "Hak Sahibi": display_name(name),
                "Toplam Destek Tutarı (TL)": amount,
                "Toplam Destek Süresi (Gün)": days,
                "Toplam Destek Süresi (Yıl)": y,
                "Toplam Destek Süresi (Ay)": m,
                "Toplam Destek Süresi (Gün Kalan)": d,
            }
        )

    df = pd.DataFrame(records)
    df = df.sort_values("Toplam Destek Tutarı (TL)", ascending=False).reset_index(drop=True)
    return df


def build_supporter_phase_dataframe(ci: CalculationInput, res: CalculationResult) -> pd.DataFrame:
    records = []

    destek_start = res.supporter_start
    destek_end = res.supporter_end

    def add_phase(name: str, start: date, end: date):
        if end <= start:
            days = 0
            y = m = d = 0
            s = e = None
        else:
            days = _interval_to_days(start, end)
            y, m, d = _interval_to_ymd(start, end)
            s, e = start, end
        records.append(
            {
                "Dönem": name,
                "Başlangıç": s,
                "Bitiş": e,
                "Süre (Gün)": days,
                "Süre (Yıl)": y,
                "Süre (Ay)": m,
                "Süre (Gün Kalan)": d,
            }
        )

    # Toplam
    add_phase("Toplam Destek Süresi", destek_start, destek_end)

    # Geçmiş dönem
    olay = ci.olay_tarihi
    hesap = ci.hesap_tarihi
    past_start = max(destek_start, olay)
    past_end = min(destek_end, hesap)
    add_phase("Geçmiş Dönem", past_start, past_end)

    # Aktif
    active_start_date = _add_years(ci.destek.birth, ci.active_start_age)
    active_end_date = _add_years(ci.destek.birth, ci.active_end_age)

    future_active_start = max(destek_start, hesap, active_start_date)
    future_active_end = min(destek_end, active_end_date)
    add_phase("Gelecek Aktif Dönem", future_active_start, future_active_end)

    # Pasif
    future_passive_start = max(destek_start, hesap, active_end_date)
    future_passive_end = destek_end
    add_phase("Gelecek Pasif Dönem", future_passive_start, future_passive_end)

    df = pd.DataFrame(records)
    return df
