from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from calculator import compute_support
from full_report import build_full_report
from legal_loader import LegalRepository
from models import (
    CalculationInput,
    Dependent,
    DependentType,
    Gender,
    IncomeMode,
    LifeTableType,
    PassiveIncomeType,
    ProfileType,
    SGKDeductionType,
    Person,
)
from profiles import apply_expert_profile, apply_yargitay_profile
from report import (
    build_supporter_phase_dataframe,
    build_summary_dataframe,
    build_yearly_dataframe,
)

# --------------------------------------------------------------------
# Genel ayarlar
# --------------------------------------------------------------------

st.set_page_config(
    page_title="Destekten Yoksun Kalma Tazminatı Hesaplama",
    layout="wide",
)

st.title("Destekten Yoksun Kalma Tazminatı Hesaplama Aracı")
st.caption(
    "Bu arayüz, profesyonel aktüeryal hesap motorunu kullanarak "
    "destekten yoksun kalma tazminatı hesabı ve ayrıntılı bilirkişi raporu üretir."
)

# Hukuki metin veri tabanı (global, bir kez yüklensin)
LEGAL_REPO = LegalRepository(base_dir=Path("legal_texts"))
try:
    LEGAL_REPO.load()
except Exception:
    # Klasör yoksa veya içinde geçerli .md yoksa da sorun değil; rapor yine üretilir.
    pass


# --------------------------------------------------------------------
# Yardımcı küçük fonksiyonlar
# --------------------------------------------------------------------


def _gender_from_label(label: str) -> Gender:
    return Gender.MALE if label == "Erkek" else Gender.FEMALE


# --------------------------------------------------------------------
# 1. GİRİŞ BİLGİLERİ (DESTEKÇİ VE TARİHLER)
# --------------------------------------------------------------------

st.header("1. Destekçi ve Tarih Bilgileri")

col_d1, col_d2, col_d3 = st.columns((2, 1, 1))
with col_d1:
    destek_name = st.text_input("Destekçinin Adı Soyadı", value="Maktul")
with col_d2:
    destek_birth = st.date_input("Destekçinin Doğum Tarihi", value=date(1985, 1, 1))
with col_d3:
    g_label = st.radio("Destekçinin Cinsiyeti", ["Erkek", "Kadın"], horizontal=True)
    destek_gender = _gender_from_label(g_label)

olay_tarihi = st.date_input("Olay Tarihi", value=date(2020, 1, 1))
hesap_tarihi = st.date_input("Hesap Tarihi", value=date.today())

destek_person = Person(name=destek_name, birth=destek_birth, gender=destek_gender)

st.markdown("---")

# --------------------------------------------------------------------
# 2. PROFİL VE TEMEL HESAP AYARLARI
# --------------------------------------------------------------------

st.header("2. Profil ve Temel Hesap Ayarları")

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    profile_label = st.selectbox(
        "Hesap Profili",
        [
            ("Yargıtay Modu", ProfileType.YARGITAY),
            ("Bilirkişi Esnek Modu", ProfileType.EXPERT),
        ],
        format_func=lambda x: x[0],
    )
    profile = profile_label[1]

with col_p2:
    life_table = st.selectbox(
        "Yaşam Tablosu",
        [LifeTableType.TRH2010, LifeTableType.PMF1931],
    )

with col_p3:
    report_discount_rate = st.number_input(
        "Rapor İskonto Oranı (Gelecek Yıllar için %)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
    )

st.markdown("---")

# --------------------------------------------------------------------
# 3. GELİR BİLGİLERİ
# --------------------------------------------------------------------

st.header("3. Gelir Bilgileri")

income_mode = st.radio(
    "Gelir Türü",
    [IncomeMode.ASGARI, IncomeMode.MANUAL],
    format_func=lambda x: x.value,
    horizontal=True,
)

monthly_income = 0.0
regular_extra = 0.0

if income_mode == IncomeMode.MANUAL:
    c1, c2 = st.columns(2)
    with c1:
        monthly_income = st.number_input(
            "Aylık Net Gelir (TL)",
            min_value=0.0,
            step=500.0,
        )
    with c2:
        regular_extra = st.number_input(
            "Düzenli Ek Gelir (Ayda, TL)",
            min_value=0.0,
            step=100.0,
        )
    st.info(
        "Manuel gelir modunda, bordro / SGK kayıtları gibi belgelere dayanan "
        "gerçek gelir tutarı üzerinden hesap yapılır."
    )
else:
    st.info(
        "Asgari ücret modunda, olay ve hesap tarihleri arasındaki her dönem için "
        "ilgili yılın net asgari ücreti ve mevzuat (AGİ vb.) dikkate alınır."
    )

st.markdown("---")

# --------------------------------------------------------------------
# 4. AKTİF / PASİF DÖNEM PARAMETRELERİ
# --------------------------------------------------------------------

st.header("4. Aktif / Pasif Dönem Parametreleri")

col_ap1, col_ap2 = st.columns(2)
with col_ap1:
    active_start_age = st.number_input(
        "Aktif Dönem Başlangıç Yaşı",
        min_value=10,
        max_value=30,
        value=18,
    )
    active_end_age = st.number_input(
        "Aktif Dönem Bitiş Yaşı",
        min_value=40,
        max_value=80,
        value=60,
    )

with col_ap2:
    passive_type = st.selectbox(
        "Pasif Dönem Gelir Türü",
        [PassiveIncomeType.PASSIVE_MIN_WAGE, PassiveIncomeType.PASSIVE_RATIO],
        format_func=lambda x: x.value,
    )
    passive_ratio = st.slider(
        "Pasif Gelir Oranı (Aktif Gelirin %)",
        min_value=0.10,
        max_value=1.00,
        value=0.70,
        step=0.05,
    )

st.markdown("---")

# --------------------------------------------------------------------
# 5. ÇOCUK DESTEK YAŞLARI
# --------------------------------------------------------------------

st.header("5. Çocuk Destek Yaşları")

col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    child_support_age_male = st.number_input(
        "Erkek Çocuk Destek Yaşı",
        min_value=18,
        max_value=30,
        value=18,
    )
with col_c2:
    child_support_age_female_non_student = st.number_input(
        "Kız Çocuk Destek Yaşı (Öğrenci Değil)",
        min_value=18,
        max_value=30,
        value=22,
    )
with col_c3:
    child_support_age_student = st.number_input(
        "Öğrenci Çocuk Destek Yaşı",
        min_value=18,
        max_value=30,
        value=25,
    )

st.markdown("---")

# --------------------------------------------------------------------
# 6. SGK, KUSUR VE AGİ
# --------------------------------------------------------------------

st.header("6. SGK, Kusur ve AGİ Parametreleri")

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    sgk_monthly_income = st.number_input(
        "SGK Aylık Gelir (TL)",
        min_value=0.0,
        step=100.0,
    )
    sgk_psd_factor = st.number_input(
        "SGK Peşin Sermaye Değeri Katsayısı",
        min_value=1.0,
        max_value=20.0,
        value=12.0,
        step=0.5,
    )
with col_s2:
    sgk_ded_type = st.selectbox(
        "SGK İndirimi",
        [SGKDeductionType.NONE, SGKDeductionType.HALF, SGKDeductionType.FULL],
        format_func=lambda x: x.value,
    )
with col_s3:
    fault_rate_percent = st.number_input(
        "Destek / Davacılar Aleyhine Kusur Oranı (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
    )
    agi_use_family_status = st.checkbox(
        "AGİ Hesabında Eş ve Çocuk Sayısını Dikkate Al",
        value=True,
    )

fault_rate = fault_rate_percent / 100.0

st.markdown("---")

# --------------------------------------------------------------------
# 7. ASKERLİK, YETİŞTİRME GİDERİ, EVLİLİK VARSAYIMLARI
# --------------------------------------------------------------------

st.header("7. Askerlik, Yetiştirme Gideri ve Evlilik Varsayımları")

col_m, col_t, col_b = st.columns(3)

with col_m:
    military_enabled = st.checkbox("Askerlik Süresini Tazminat Dışı Bırak")
    military_start_age = st.number_input(
        "Askerlik Başlangıç Yaşı",
        min_value=18,
        max_value=40,
        value=20,
    )
    military_duration_months = st.number_input(
        "Askerlik Süresi (Ay)",
        min_value=0,
        max_value=36,
        value=12,
    )

with col_t:
    training_enabled = st.checkbox("Yetiştirme Gideri Hesapla (18 yaş altı destek)")
    training_rate = (
        st.number_input(
            "Yetiştirme Gideri Oranı (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
        )
        / 100.0
    )
    training_base_monthly = st.number_input(
        "Yetiştirme Giderine Esas Aylık (0 = Asgari Ücret)",
        min_value=0.0,
        step=500.0,
    )
    mother_working = st.checkbox("Anne Çalışıyor", value=True)
    father_working = st.checkbox("Baba Çalışıyor", value=True)

with col_b:
    apply_ayim = st.checkbox("Dul Eş için AYİM Evlenme İndirimi Uygula", value=True)
    assume_marriage_if_single = st.checkbox("Destek Bekâr ise Varsayılan Evlilik/Çocuk Senaryosu")
    assumed_marriage_age = st.number_input(
        "Varsayılan Evlilik Yaşı",
        min_value=18,
        max_value=40,
        value=25,
    )
    assumed_child1_after_years = st.number_input(
        "İlk Çocuğun Evlilikten Sonra (Yıl)",
        min_value=1,
        max_value=10,
        value=2,
    )
    assumed_child2_after_years = st.number_input(
        "İkinci Çocuğun Evlilikten Sonra (Yıl)",
        min_value=1,
        max_value=10,
        value=4,
    )
    assumed_spouse_has_income = st.checkbox("Varsayılan Eşin Geliri Var", value=False)

st.markdown("---")

# --------------------------------------------------------------------
# 8. ANNE-BABA PAY HAVUZU
# --------------------------------------------------------------------

st.header("8. Anne-Baba Pay Parametreleri")

col_p, col_cap = st.columns(2)
with col_p:
    separate_parent_pool = st.checkbox(
        "Anne-Baba Payları Eş/Çocuklardan Ayrı Havuz Olsun",
        value=True,
    )
with col_cap:
    parent_share_cap_25_enabled = st.checkbox(
        "Anne-Baba Toplam Payı %25'i Geçmesin",
        value=True,
    )

st.markdown("---")

# --------------------------------------------------------------------
# 9. HAK SAHİPLERİ (BAĞIMLILAR)
# --------------------------------------------------------------------

st.header("9. Destekten Yararlananlar (Hak Sahipleri)")
st.write(
    "Aşağıda eş, çocuklar ve anne-baba için bilgileri doldurun. İsterseniz "
    "yalnızca ilgili kutucukları işaretleyerek sınırlı sayıda hak sahibiyle "
    "çalışabilirsiniz."
)

deps: List[Dependent] = []

# EŞ
with st.expander("Eş Bilgileri", expanded=False):
    has_spouse = st.checkbox("Eş Var", value=False, key="has_spouse")
    if has_spouse:
        col_es1, col_es2, col_es3 = st.columns(3)
        with col_es1:
            es_name = st.text_input("Eş Adı", value="Eş")
        with col_es2:
            es_birth = st.date_input("Eş Doğum Tarihi", value=date(1987, 1, 1))
        with col_es3:
            es_gender_label = st.radio(
                "Eş Cinsiyeti",
                ["Kadın", "Erkek"],
                horizontal=True,
                key="es_gender",
            )
            es_gender = Gender.FEMALE if es_gender_label == "Kadın" else Gender.MALE

        es_has_income = st.checkbox("Eşin Kendi Geliri Var", value=False)
        es_exit_date = None
        es_exit_enabled = st.checkbox(
            "Eş için Destekten Çıkış Tarihi Belirt",
            value=False,
        )
        if es_exit_enabled:
            es_exit_date = st.date_input("Eş Destekten Çıkış Tarihi", key="es_exit_date")

        deps.append(
            Dependent(
                person=Person(es_name, es_birth, es_gender),
                dep_type=DependentType.SPOUSE,
                has_income=es_has_income,
                apply_marriage_discount=apply_ayim,
                custom_exit_date=es_exit_date,
            )
        )

# ÇOCUKLAR
with st.expander("Çocuk Bilgileri", expanded=False):
    num_children = st.number_input(
        "Çocuk Sayısı",
        min_value=0,
        max_value=6,
        value=0,
        step=1,
    )
    for i in range(int(num_children)):
        st.markdown(f"**Çocuk {i + 1}**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ch_name = st.text_input(
                f"Ad {i + 1}",
                value=f"Çocuk {i + 1}",
                key=f"child_name_{i}",
            )
        with c2:
            ch_birth = st.date_input(
                f"Doğum Tarihi {i + 1}",
                value=date(2015, 1, 1),
                key=f"child_birth_{i}",
            )
        with c3:
            ch_gender_label = st.radio(
                f"Cinsiyet {i + 1}",
                ["Erkek", "Kadın"],
                horizontal=True,
                key=f"child_gender_{i}",
            )
            ch_gender = _gender_from_label(ch_gender_label)
        with c4:
            is_student = st.checkbox(
                "Öğrenci",
                value=False,
                key=f"child_student_{i}",
            )

        ch_exit_date = None
        ch_exit_enabled = st.checkbox(
            "Bu çocuk için özel destekten çıkış tarihi belirt",
            key=f"child_exit_en_{i}",
            value=False,
        )
        if ch_exit_enabled:
            ch_exit_date = st.date_input(
                "Destekten Çıkış Tarihi",
                key=f"child_exit_{i}",
            )

        deps.append(
            Dependent(
                person=Person(ch_name, ch_birth, ch_gender),
                dep_type=DependentType.CHILD,
                is_student=is_student,
                custom_exit_date=ch_exit_date,
            )
        )

# ANNE
with st.expander("Anne Bilgileri", expanded=False):
    has_mother = st.checkbox("Anne Destekten Yoksun", value=False)
    if has_mother:
        a1, a2 = st.columns(2)
        with a1:
            aname = st.text_input("Anne Adı", value="Anne")
        with a2:
            abirth = st.date_input("Anne Doğum Tarihi", value=date(1955, 1, 1))
        reduced_a = st.checkbox("Anne Payı Çocuk Payının Yarısı Olsun")
        a_exit_date = None
        a_exit_enabled = st.checkbox(
            "Anne için Destekten Çıkış Tarihi Belirt",
            value=False,
        )
        if a_exit_enabled:
            a_exit_date = st.date_input(
                "Anne Destekten Çıkış Tarihi",
                key="mother_exit_date",
            )
        deps.append(
            Dependent(
                person=Person(aname, abirth, Gender.FEMALE),
                dep_type=DependentType.MOTHER,
                reduced_share=reduced_a,
                custom_exit_date=a_exit_date,
            )
        )

# BABA
with st.expander("Baba Bilgileri", expanded=False):
    has_father = st.checkbox("Baba Destekten Yoksun", value=False)
    if has_father:
        b1, b2 = st.columns(2)
        with b1:
            bname = st.text_input("Baba Adı", value="Baba")
        with b2:
            bbirth = st.date_input("Baba Doğum Tarihi", value=date(1950, 1, 1))
        reduced_b = st.checkbox("Baba Payı Çocuk Payının Yarısı Olsun")
        b_exit_date = None
        b_exit_enabled = st.checkbox(
            "Baba için Destekten Çıkış Tarihi Belirt",
            value=False,
        )
        if b_exit_enabled:
            b_exit_date = st.date_input(
                "Baba Destekten Çıkış Tarihi",
                key="father_exit_date",
            )
        deps.append(
            Dependent(
                person=Person(bname, bbirth, Gender.MALE),
                dep_type=DependentType.FATHER,
                reduced_share=reduced_b,
                custom_exit_date=b_exit_date,
            )
        )

st.markdown("---")

# --------------------------------------------------------------------
# 10. HESAPLAMA BUTONU
# --------------------------------------------------------------------

st.header("10. Hesaplama ve Sonuçlar")

if st.button("💻 Destekten Yoksun Kalma Tazminatını Hesapla"):
    # 1) CalculationInput oluştur
    ci = CalculationInput(
        olay_tarihi=olay_tarihi,
        hesap_tarihi=hesap_tarihi,
        destek=destek_person,
        income_mode=income_mode,
    )

    # Önce profil uygulanır (varsayılan ayarlar)
    if profile == ProfileType.YARGITAY:
        ci = apply_yargitay_profile(ci)
    else:
        ci = apply_expert_profile(ci)

    # Sonra kullanıcı seçimleriyle override edilir (kullanıcı daima kazanır)
    ci.life_table = life_table
    ci.monthly_income = monthly_income
    ci.regular_extra_income = regular_extra

    ci.active_start_age = int(active_start_age)
    ci.active_end_age = int(active_end_age)
    ci.passive_income_type = passive_type
    ci.passive_ratio = float(passive_ratio)

    ci.child_support_age_male = int(child_support_age_male)
    ci.child_support_age_female_non_student = int(child_support_age_female_non_student)
    ci.child_support_age_student = int(child_support_age_student)

    ci.report_discount_rate = float(report_discount_rate)

    ci.separate_parent_pool = separate_parent_pool
    ci.parent_share_cap_25_enabled = parent_share_cap_25_enabled

    ci.sgk_monthly_income = float(sgk_monthly_income)
    ci.sgk_psd_factor = float(sgk_psd_factor)
    ci.sgk_deduction_type = sgk_ded_type

    ci.fault_rate = float(fault_rate)

    ci.apply_ayim = apply_ayim

    ci.training_enabled = training_enabled
    ci.training_rate = float(training_rate)
    ci.training_base_monthly = float(training_base_monthly)
    ci.mother_working = mother_working
    ci.father_working = father_working

    ci.military_enabled = military_enabled
    ci.military_start_age = int(military_start_age)
    ci.military_duration_months = int(military_duration_months)

    ci.assume_marriage_if_single = assume_marriage_if_single
    ci.assumed_marriage_age = int(assumed_marriage_age)
    ci.assumed_child1_after_years = int(assumed_child1_after_years)
    ci.assumed_child2_after_years = int(assumed_child2_after_years)
    ci.assumed_spouse_has_income = assumed_spouse_has_income

    ci.agi_use_family_status = agi_use_family_status

    ci.profile = profile
    ci.dependents = deps

    # 2) HESABI ÇALIŞTIR
    res = compute_support(ci)

    # 3) TABLOLAR
    df_years = build_yearly_dataframe(res)
    df_summary = build_summary_dataframe(ci, res)
    df_phases = build_supporter_phase_dataframe(ci, res)

    # 4) TAM RAPOR
    rapor_metin = build_full_report(ci, res, LEGAL_REPO, df_years, df_summary, df_phases)

    st.success("Hesaplama tamamlandı.")

    tab_ozet, tab_yillik, tab_faz, tab_rapor = st.tabs(
        ["📊 Özet Tablo", "📅 Yıllık Tablo", "📐 Destek Dönemleri", "📄 Tam Rapor"]
    )

    with tab_ozet:
        st.subheader("Özet Tablo")
        st.dataframe(df_summary)

    with tab_yillik:
        st.subheader("Yıllık Hesap Tablosu")
        st.dataframe(df_years)

    with tab_faz:
        st.subheader("Destekçinin Aktif / Pasif ve Diğer Dönemleri")
        st.dataframe(df_phases)

    with tab_rapor:
        st.subheader("Tam Bilirkişi Raporu")
        st.text_area("Rapor Metni", rapor_metin, height=600)
        st.download_button(
            label="Raporu .txt olarak indir",
            data=rapor_metin,
            file_name="destekten_yoksun_kalma_raporu.txt",
            mime="text/plain",
        )
else:
    st.info("Lütfen yukarıdaki bilgileri doldurup 'Hesapla' düğmesine basın.")
