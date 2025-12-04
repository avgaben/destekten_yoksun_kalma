from __future__ import annotations

from copy import deepcopy

from models import CalculationInput, ProfileType, LifeTableType


def apply_yargitay_profile(ci: CalculationInput) -> CalculationInput:
    """
    Daha muhafazakâr, Yargıtay içtihatlarına yakın varsayımlar.
    Burada sen kendi pratiğine göre ince ayar yapabilirsin.
    """
    c = deepcopy(ci)
    c.life_table = LifeTableType.TRH2010
    c.active_start_age = 18
    c.active_end_age = 60
    c.passive_ratio = 0.70
    c.report_discount_rate = 0.0
    c.assume_marriage_if_single = True
    c.assumed_marriage_age = 25
    c.assumed_child1_after_years = 2
    c.assumed_child2_after_years = 4
    c.parent_share_cap_25_enabled = True
    return c


def apply_expert_profile(ci: CalculationInput) -> CalculationInput:
    """
    Bilirkişinin kendi parametreleriyle esnek çalışma modu.
    Şu anda sadece pas-through; istersen burada default'ları değiştirebilirsin.
    """
    return ci
