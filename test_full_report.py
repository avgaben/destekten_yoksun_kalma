from datetime import date
from pathlib import Path

import pandas as pd

from models import (
    Person,
    Dependent,
    DependentType,
    Gender,
    IncomeMode,
    LifeTableType,
    PassiveIncomeType,
    ProfileType,
    CalculationInput,
)
from calculator import compute_support
from report import build_yearly_dataframe, build_summary_dataframe
from legal_loader import LegalRepository
from full_report import build_full_report


def main():
    # 1) DESTEK (maktul) bilgileri
    destek = Person(
        name="Maktul Ahmet",
        birth=date(1985, 6, 15),
        gender=Gender.MALE,
    )

    # 2) HAK SAHİPLERİ
    es = Dependent(
        person=Person(
            name="Eşi Ayşe",
            birth=date(1987, 3, 10),
            gender=Gender.FEMALE,
        ),
        dep_type=DependentType.SPOUSE,
        # Buraya gerekirse evlenme indirimi gibi ek parametreler eklenebilir;
        # models.py'deki Dependent dataclass'ına bakarak doldurabilirsin.
    )

    cocuk = Dependent(
        person=Person(
            name="Çocuk Mehmet",
            birth=date(2015, 1, 1),
            gender=Gender.MALE,
        ),
        dep_type=DependentType.CHILD,
        is_student=True,  # öğrenci kabul edelim
    )

    # 3) HESAP GİRDİSİ (CalculationInput)
    ci = CalculationInput(
        olay_tarihi=date(2024, 1, 1),
        hesap_tarihi=date(2025, 1, 1),
        destek=destek,
        income_mode=IncomeMode.ASGARI,      # Asgari ücret üzerinden hesap
    )

    # Burada CalculationInput içindeki ayrıntılı parametreleri de değiştirebilirsin:
    ci.life_table = LifeTableType.TRH2010
    ci.active_start_age = 18
    ci.active_end_age = 60
    ci.passive_income_type = PassiveIncomeType.PASSIVE_MIN_WAGE
    ci.passive_ratio = 0.70
    ci.profile = ProfileType.EXPERT        # veya ProfileType.YARGITAY

    # Bağımlıları ekle
    ci.dependents = [es, cocuk]

    # İstersen kusur, SGK, askerlik, bekâr destek vs. parametrelerini de burada set edebilirsin.
    # Örneğin:
    # ci.sgk_deduction_type = SGKDeductionType.HALF
    # ci.sgk_psd = 500000.0

    # 4) HESABI ÇALIŞTIR
    res = compute_support(ci)

    # 5) TABLOLAR
    df_years = build_yearly_dataframe(res)
    df_summary = build_summary_dataframe(ci, res)

    # df_phases şimdilik boş da olabilir, full_report bunu kontrol ediyor
    df_phases = pd.DataFrame()

    # 6) HUKUKİ METİNLER (LegalRepository)
    # Eğer legal_texts diye bir klasörün ve içinde .md formatında içtihat/metinlerin varsa,
    # o klasörü burada kullanabilirsin. Yoksa boş klasör ver, sorun çıkmaz.
    legal_dir = Path("legal_texts")
    legal_dir.mkdir(exist_ok=True)
    repo = LegalRepository(legal_dir)
    repo.load()  # İçerik yoksa da sadece boş çalışır

    # 7) TAM BİLİRKİŞİ RAPORU
    rapor_metin = build_full_report(ci, res, repo, df_years, df_summary, df_phases)

    print(rapor_metin)


if __name__ == "__main__":
    main()
