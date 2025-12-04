# topics.py
from __future__ import annotations

from enum import Enum, auto
from typing import Set

from models import (
    CalculationInput,
    CalculationResult,
    LifeTableType,
    PassiveIncomeType,
    SGKDeductionType,
    ProfileType,
    DependentType,
    Gender,
)
from calculator import _age_of


class Topic(Enum):
    TRH2010 = auto()
    PMF1931 = auto()
    DONEM_ESASI = auto()
    AKTIF_PASIF_TANIM = auto()
    PASIF_MIN_ASGARI = auto()
    PASIF_ORAN = auto()
    ASKERLIK = auto()
    YETISTIRME_GIDERI = auto()
    AYIM_EVLI_ES = auto()
    ANNE_BABA_AYRI_HAVUZ = auto()
    ANNE_BABA_25_SINIRI = auto()
    ANNE_BABA_YARIM_PAY = auto()
    BEKAR_EV_COCUK_SENARYO = auto()
    SGK_PSD = auto()
    SGK_PSD_INDIRIM_TURU = auto()
    AGI_2008_2021 = auto()
    AGI_2022_SONRASI_ISTISNA = auto()
    KUSUR_ORANI = auto()
    RAPOR_ISKONTO = auto()
    YARGITAY_MODU = auto()
    BILIRKISI_MODU = auto()


# Topic -> hangi tag'ler üzerinden snippet arayacağız?
TOPIC_TAGS = {
    Topic.TRH2010: ["TRH2010", "YaşamTablosu"],
    Topic.PMF1931: ["PMF1931", "YaşamTablosu"],
    Topic.DONEM_ESASI: ["DonemEsasi"],
    Topic.AKTIF_PASIF_TANIM: ["AktifPasif", "DonemEsasi"],
    Topic.PASIF_MIN_ASGARI: ["PasifGelir", "AsgariUcret"],
    Topic.PASIF_ORAN: ["PasifGelir", "Oran"],
    Topic.ASKERLIK: ["Askerlik"],
    Topic.YETISTIRME_GIDERI: ["YetiştirmeGideri"],
    Topic.AYIM_EVLI_ES: ["AYIM", "EvlenmeSansı"],
    Topic.ANNE_BABA_AYRI_HAVUZ: ["AnneBabaPayları", "AyrıHavuz"],
    Topic.ANNE_BABA_25_SINIRI: ["AnneBabaPayları", "YirmiBesSiniri"],
    Topic.ANNE_BABA_YARIM_PAY: ["AnneBabaPayları", "YarimPay"],
    Topic.BEKAR_EV_COCUK_SENARYO: ["BekarVarsayımı"],
    Topic.SGK_PSD: ["SGK", "PSD"],
    Topic.SGK_PSD_INDIRIM_TURU: ["SGK", "PSD", "Isveren", "UcuncuKisi"],
    Topic.AGI_2008_2021: ["AGI", "AsgariUcret"],
    Topic.AGI_2022_SONRASI_ISTISNA: ["AGI", "2022Sonrasi"],
    Topic.KUSUR_ORANI: ["KusurOrani"],
    Topic.RAPOR_ISKONTO: ["RaporIskonto"],
    Topic.YARGITAY_MODU: ["YargıtayModu"],
    Topic.BILIRKISI_MODU: ["BilirkişiModu"],
}


def determine_active_topics(ci: CalculationInput, res: CalculationResult) -> Set[Topic]:
    topics: Set[Topic] = set()

    # Yaşam tablosu
    if ci.life_table == LifeTableType.TRH2010:
        topics.add(Topic.TRH2010)
    elif ci.life_table == LifeTableType.PMF1931:
        topics.add(Topic.PMF1931)

    # Her hesapta dönem esası ve aktif/pasif tanımı vardır
    topics.add(Topic.DONEM_ESASI)
    topics.add(Topic.AKTIF_PASIF_TANIM)

    # Pasif dönem gelir tipi
    if ci.passive_income_type == PassiveIncomeType.PASSIVE_MIN_WAGE:
        topics.add(Topic.PASIF_MIN_ASGARI)
    elif ci.passive_income_type == PassiveIncomeType.PASSIVE_RATIO:
        topics.add(Topic.PASIF_ORAN)

    # Askerlik
    if getattr(ci, "military_enabled", False) and ci.destek.gender == Gender.MALE:
        topics.add(Topic.ASKERLIK)

    # Yetiştirme gideri (kazalı 18 yaş altı ise gerçekten uygulanıyor)
    if getattr(ci, "training_enabled", False):
        age_at_olay = _age_of(ci.destek.birth, ci.olay_tarihi)
        if age_at_olay < 18.0:
            topics.add(Topic.YETISTIRME_GIDERI)

    # AYİM evlenme şansı (eş varsa ve uygulanıyorsa)
    if getattr(ci, "apply_ayim", True):
        has_spouse = any(d.dep_type == DependentType.SPOUSE for d in ci.dependents)
        if has_spouse:
            topics.add(Topic.AYIM_EVLI_ES)

    # Anne-baba havuzu / %25 sınırı / yarım pay
    if getattr(ci, "separate_parent_pool", False):
        topics.add(Topic.ANNE_BABA_AYRI_HAVUZ)
    if getattr(ci, "parent_share_cap_25_enabled", False):
        topics.add(Topic.ANNE_BABA_25_SINIRI)
    if any(d.dep_type in (DependentType.MOTHER, DependentType.FATHER) and d.reduced_share
           for d in ci.dependents):
        topics.add(Topic.ANNE_BABA_YARIM_PAY)

    # Bekâr için varsayılan evlilik/çocuk
    if getattr(ci, "assume_marriage_if_single", False):
        topics.add(Topic.BEKAR_EV_COCUK_SENARYO)

    # SGK PSD
    if ci.sgk_monthly_income > 0:
        topics.add(Topic.SGK_PSD)
        if ci.sgk_deduction_type != SGKDeductionType.NONE:
            topics.add(Topic.SGK_PSD_INDIRIM_TURU)

    # AGİ / vergi istisnası: yıllara bak
    years = {row.year for row in res.rows}
    if ci.agi_use_family_status and any(2008 <= y <= 2021 for y in years):
        topics.add(Topic.AGI_2008_2021)
    if any(y >= 2022 for y in years):
        topics.add(Topic.AGI_2022_SONRASI_ISTISNA)

    # Kusur
    if ci.fault_rate > 0:
        topics.add(Topic.KUSUR_ORANI)

    # Rapor iskontosu
    if ci.report_discount_rate > 0:
        topics.add(Topic.RAPOR_ISKONTO)

    # Profil
    if ci.profile == ProfileType.YARGITAY:
        topics.add(Topic.YARGITAY_MODU)
    elif ci.profile == ProfileType.EXPERT:
        topics.add(Topic.BILIRKISI_MODU)

    return topics
