from __future__ import annotations

from typing import Dict, List

from models import CalculationInput, DependentType


def base_shares(ci: CalculationInput) -> Dict[str, float]:
    """
    2–1–1 sistemine göre temel paylar:
      - Destek: 2
      - Eş: 2
      - Çocuk: 1
      - Anne/Baba: 1 (reduced_share=True ise 0.5)
    Bu paylar sadece oranları belirlemek için kullanılır.
    """
    shares: Dict[str, float] = {}
    shares["destek"] = 2.0

    for d in ci.dependents:
        key = d.person.name
        if d.dep_type == DependentType.SPOUSE:
            shares[key] = 2.0
        elif d.dep_type == DependentType.CHILD:
            shares[key] = 1.0
        elif d.dep_type in (DependentType.MOTHER, DependentType.FATHER):
            shares[key] = 0.5 if d.reduced_share else 1.0
        else:
            shares[key] = 1.0

    return shares


def parent_names(ci: CalculationInput) -> List[str]:
    names = []
    for d in ci.dependents:
        if d.dep_type in (DependentType.MOTHER, DependentType.FATHER):
            names.append(d.person.name)
    return names


def normalize_shares(shares: Dict[str, float]) -> Dict[str, float]:
    total = sum(shares.values())
    if total <= 0:
        return {k: 0.0 for k in shares}
    return {k: v / total for k, v in shares.items()}
