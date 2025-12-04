from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional, Dict, Tuple


class Gender(Enum):
    MALE = "Erkek"
    FEMALE = "Kadın"


class LifeTableType(Enum):
    TRH2010 = "TRH 2010"
    PMF1931 = "PMF 1931"


class IncomeMode(Enum):
    ASGARI = "Asgari Ücret"
    MANUAL = "Manuel Gelir"


class PassiveIncomeType(Enum):
    PASSIVE_MIN_WAGE = "Pasif dönemde AGİ'siz net asgari ücret"
    PASSIVE_RATIO = "Aktif gelirin oranı"


class SGKDeductionType(Enum):
    NONE = "SGK İndirimi Yok"
    HALF = "Üçüncü Kişi (%50)"
    FULL = "İşveren (%100)"


class ProfileType(Enum):
    YARGITAY = "Yargıtay Modu"
    EXPERT = "Bilirkişi Esnek Modu"


class DependentType(Enum):
    SPOUSE = "Eş"
    CHILD = "Çocuk"
    MOTHER = "Anne"
    FATHER = "Baba"
    OTHER = "Diğer"


@dataclass
class Person:
    name: str
    birth: date
    gender: Gender


@dataclass
class Dependent:
    person: Person
    dep_type: DependentType

    # Çocuk ise:
    is_student: bool = False

    # Anne/baba için: payı çocuk payının yarısı mı?
    reduced_share: bool = False

    # Evlenme şansı indirimi uygulanacak mı? (eş için)
    apply_marriage_discount: bool = True

    # AGİ açısından: bu kişinin geliri var mı? (özellikle eş için önemli)
    has_income: bool = False

    # İsteğe bağlı: bu kişi için özel destek süresi (yıl cinsinden)
    custom_support_years: Optional[float] = None

    # İsteğe bağlı: bu kişi için destekte olmanın SON tarihi (dahil değil)
    custom_exit_date: Optional[date] = None


@dataclass
class YearRow:
    year: int
    age_supporter: int
    period_type: str  # "Geçmiş", "Gelecek Aktif", "Gelecek Pasif"
    gross_support: float
    present_value: float
    shares: Dict[str, float]  # isim -> o yılki bugünkü değer


@dataclass
class CalculationInput:
    olay_tarihi: date
    hesap_tarihi: date
    destek: Person

    # Gelir
    income_mode: IncomeMode
    monthly_income: float = 0.0
    regular_extra_income: float = 0.0

    # Yaşam tablosu
    life_table: LifeTableType = LifeTableType.TRH2010

    # Aktif/pasif parametreleri
    active_start_age: int = 18
    active_end_age: int = 60
    passive_income_type: PassiveIncomeType = PassiveIncomeType.PASSIVE_MIN_WAGE
    passive_ratio: float = 0.70

    # Çocuk destek bitiş yaşları
    child_support_age_male: int = 18
    child_support_age_female_non_student: int = 22
    child_support_age_student: int = 25

    # Rapor için ek iskonto (hesap tarihinden sonraki yıllara, %)
    report_discount_rate: float = 0.0

    # Yöntem: use_progresif=True ise report_discount_rate,
    # False ise technical_interest kullanılır.
    use_progresif: bool = True
    technical_interest: float = 1.80

    # Pay parametreleri
    separate_parent_pool: bool = True
    parent_share_cap_25_enabled: bool = True  # Anne-baba toplamı %25'i aşmasın

    # SGK
    sgk_monthly_income: float = 0.0
    sgk_deduction_type: SGKDeductionType = SGKDeductionType.NONE
    sgk_psd_factor: float = 12.0  # basit katsayı

    # Kusur
    fault_rate: float = 0.0  # %

    # Evlenme şansı indirimi (eş için AYİM tablosu)
    apply_ayim: bool = True

    # Yetiştirme gideri
    training_enabled: bool = False
    training_rate: float = 0.05  # %5
    training_base_monthly: float = 0.0  # 0 ise asgari ücretten alınır
    mother_working: bool = True
    father_working: bool = True

    # Askerlik
    military_enabled: bool = False
    military_start_age: int = 20
    military_duration_months: int = 12

    # Bekâr destek → farazi evlilik/çocuk varsayımı
    assume_marriage_if_single: bool = False
    assumed_marriage_age: int = 25
    assumed_child1_after_years: int = 2
    assumed_child2_after_years: int = 4
    assumed_spouse_has_income: bool = False

    # AGİ: eş ve çocuk sayısına göre hesaplama
    agi_use_family_status: bool = True

    # Profil
    profile: ProfileType = ProfileType.EXPERT

    # Bağımlılar
    dependents: List[Dependent] = field(default_factory=list)


@dataclass
class CalculationResult:
    rows: List[YearRow]
    total_support: float
    total_by_person: Dict[str, float]
    sgk_psd_deduction: float
    total_after_sgk: float
    total_after_fault: float
    training_total: float

    # Destek aralığı
    supporter_start: date
    supporter_end: date
    # Gerçek bağımlıların destek aralığı (yoksa None)
    dependent_intervals: Dict[str, Optional[Tuple[date, date]]]
    # Varsayılan eş/çocuklar için aralıklar
    virtual_intervals: Dict[str, Tuple[date, date]]
