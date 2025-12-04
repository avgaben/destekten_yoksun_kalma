from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from models import LifeTableType, Gender


@dataclass
class LifeTable:
    ex: Dict[Tuple[Gender, int], float]  # (gender, age) -> life expectancy (years)


_tables_cache: Dict[LifeTableType, LifeTable] = {}


def _load_table(table_type: LifeTableType) -> LifeTable:
    if table_type in _tables_cache:
        return _tables_cache[table_type]

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    if table_type == LifeTableType.TRH2010:
        path = data_dir / "trh2010.csv"
    else:
        path = data_dir / "pmf1931.csv"

    ex_map: Dict[Tuple[Gender, int], float] = {}

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                age = int(row["age"])
                m_ex = float(row["male_ex"])
                f_ex = float(row["female_ex"])
                ex_map[(Gender.MALE, age)] = m_ex
                ex_map[(Gender.FEMALE, age)] = f_ex
    else:
        # Tablo yoksa kaba bir fallback (tam aktüerya için gerçek tabloyu koyman gerek)
        for age in range(0, 111):
            if table_type == LifeTableType.TRH2010:
                # Çok basit yaklaşık: 0 yaşta 78 yıl, sonra lineer azalsın
                base = 78.0 if age == 0 else max(0.0, 78.0 - age)
            else:
                base = 70.0 if age == 0 else max(0.0, 70.0 - age)
            ex_map[(Gender.MALE, age)] = base
            ex_map[(Gender.FEMALE, age)] = base + 3.0

    lt = LifeTable(ex=ex_map)
    _tables_cache[table_type] = lt
    return lt


def get_life_expectancy(age: int, table_type: LifeTableType, gender: Gender) -> float:
    """
    Verilen yaş ve cinsiyet için bakiye ömrü (yıl) döndürür.
    Yaş tablonun dışında ise en yakın sınır kullanılır.
    """
    if age < 0:
        age = 0
    if age > 110:
        age = 110

    table = _load_table(table_type)
    if (gender, age) in table.ex:
        return table.ex[(gender, age)]

    # En yakın yaşı bul
    ages = [a for (g, a) in table.ex.keys() if g == gender]
    if not ages:
        return 0.0
    closest = min(ages, key=lambda a: abs(a - age))
    return table.ex[(gender, closest)]
