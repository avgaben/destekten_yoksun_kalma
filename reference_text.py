# reference_text.py

"""
Bu modül, destekten yoksun kalma tazminatı hesabında kullanılan
parametreleri (yaşam tablosu, gelir modu, pasif gelir, SGK indirimi,
profil, iskonto, AYİM, yetiştirme gideri vb.) raporda hukukî ve
aktüeryal olarak açıklamak için yardımcı fonksiyonlar içerir.

Kullanım örneği (full_report.py içinde):

    from models import CalculationInput
    from reference_text import build_parameter_explanation

    def build_full_report(ci: CalculationInput, res: CalculationResult, ...):
        param_text = build_parameter_explanation(ci)
        ...
        rapor = []
        rapor.append("HUKUKİ VE TEKNİK ESASLAR")
        rapor.append(param_text)
        ...

Parametre açıklamaları, kullandığınız enum ve alanlara göre dinamik üretilir.
"""

from __future__ import annotations

from typing import List

from models import (
    CalculationInput,
    LifeTableType,
    IncomeMode,
    PassiveIncomeType,
    SGKDeductionType,
    ProfileType,
)


# ---------------------------------------------------------------------------
# 1) YAŞAM TABLOSU AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_life_table_choice(life_table: LifeTableType) -> str:
    if life_table == LifeTableType.TRH2010:
        return (
            "Bu dosyada destekçinin ve hak sahiplerinin bakiye ömürlerinin "
            "belirlenmesinde, Türkiye'ye özgü güncel demografik verilerle "
            "hazırlanmış TRH 2010 yaşam tablosu esas alınmıştır. Bu tablo, "
            "PMF 1931'e göre daha güncel ve gerçekçi kabul edildiğinden, "
            "aktüeryal açıdan isabetli sonuçlar verdiği doktrinde ifade "
            "edilmektedir."
        )
    elif life_table == LifeTableType.PMF1931:
        return (
            "Bu dosyada bakiye ömürler, uzun yıllar uygulamada kullanılmış olan "
            "PMF 1931 yaşam tablosuna göre belirlenmiştir. Bu tablo güncel "
            "demografik yapıyı tam olarak yansıtmasa da, özellikle önceki "
            "uygulamalarla uyum ve karşılaştırma yapma amacıyla tercih "
            "edilebilmekte, mahkemenin takdirine sunulmaktadır."
        )
    else:
        # İleride yeni tablo eklerseniz buraya açıklama yazabilirsiniz.
        return (
            "Bu dosyada bakiye ömürlerin belirlenmesinde seçilen yaşam tablosu "
            "mahkemenin ve doktrinin benimsediği genel esaslara uygun olarak "
            "kullanılmıştır."
        )


# ---------------------------------------------------------------------------
# 2) GELİR MODU (ASGARİ / MANUEL) AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_income_mode(ci: CalculationInput) -> str:
    if ci.income_mode == IncomeMode.ASGARI:
        return (
            "Destekçinin gerçek ve belgeli geliri açısından dosya kapsamındaki "
            "veriler değerlendirilmiş; düzenli, ispatlı ve istikrarlı bir gelir "
            "düzeyi ortaya konulamadığından, Yargıtay uygulamasında da sıkça "
            "benimsendiği üzere asgari ücret esas alınmıştır. Hesapta olay ve "
            "hesap tarihleri arasındaki dönemler için ilgili yılların net asgari "
            "ücretleri dikkate alınmış, mevzuattaki değişiklikler (AGİ, vergi "
            "istisnası vb.) dönemler itibarıyla gözetilmiştir."
        )
    elif ci.income_mode == IncomeMode.MANUAL:
        return (
            "Destekçinin gerçek geliri; bordro, SGK kayıtları, sözleşmeler ve "
            "dosyadaki diğer deliller birlikte değerlendirilerek belirlenmiş, "
            "hesaplamada bu gerçek (manuel) gelir esas alınmıştır. Gelir, "
            "dönemsel artışlar ve fiili çalışma koşulları dikkate alınarak "
            "aktüeryal hesaba yansıtılmıştır."
        )
    else:
        return (
            "Destekçinin gelir seviyesi, dosya kapsamındaki deliller ve "
            "yerleşik içtihatlar dikkate alınarak belirlenmiş ve aktüeryal "
            "hesaplamanın temel girdisi olarak kullanılmıştır."
        )


# ---------------------------------------------------------------------------
# 3) AKTİF / PASİF DÖNEM VE PASİF GELİR AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_active_passive(ci: CalculationInput) -> str:
    return (
        "Hesaplamada, destekçinin çalışma yaşamı aktüeryal teamüllere uygun "
        f"olarak {ci.active_start_age} yaşında başlayıp {ci.active_end_age} "
        "yaşına kadar süren 'aktif dönem' ve sonrasını kapsayan 'pasif dönem' "
        "olarak ikiye ayrılmıştır. Aktif dönemde destekçinin fiilen çalışma "
        "ve gelir elde etme olanağı bulunduğu; pasif dönemde ise gelirinin "
        "azalarak emeklilik düzeyine indiği kabul edilmiştir."
    )


def explain_passive_income(ci: CalculationInput) -> str:
    if ci.passive_income_type == PassiveIncomeType.PASSIVE_MIN_WAGE:
        return (
            "Pasif dönem için, emeklilik sonrası gelir seviyesinin asgari "
            "ücret düzeyine yaklaşacağı kabul edilmiş ve bu nedenle pasif "
            "dönemde AGİ'siz net asgari ücret esas alınmıştır. Bu varsayım, "
            "özellikle emekli aylıklarının çoğu zaman asgari ücret düzeyine "
            "yakınsadığına ilişkin aktüeryal ve sosyoekonomik gözlemlerle "
            "uyumludur."
        )
    elif ci.passive_income_type == PassiveIncomeType.PASSIVE_RATIO:
        return (
            f"Pasif dönem için, destekçinin gelirinin aktif döneme göre azalacağı "
            f"varsayılmış ve pasif dönem yıllık geliri aktif gelirinin "
            f"{ci.passive_ratio:.0%} oranı üzerinden hesaplanmıştır. Böylece "
            "emeklilik döneminde fiili çalışma gelirinin kısmen azalarak devam "
            "ettiği kabul edilmiştir."
        )
    else:
        return (
            "Pasif dönem gelirine ilişkin varsayımlar, somut olayın koşulları ve "
            "doktrindeki kabul gören aktüeryal yaklaşımlar çerçevesinde belirlenmiş "
            "ve hesaplamaya bu şekilde yansıtılmıştır."
        )


# ---------------------------------------------------------------------------
# 4) PROFİL (YARGITAY / BİLİRKİŞİ ESNEK MODU) AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_profile(ci: CalculationInput) -> str:
    if ci.profile == ProfileType.YARGITAY:
        return (
            "Destek paylarının eş, çocuk, anne ve baba arasında dağıtımında, "
            "Yargıtay'ın yerleşik içtihatlarında kabul gören profil ve pay "
            "çizelgeleri esas alınmış; desteğin kendi tüketim payı ile hak "
            "sahiplerinin payları bu çizelgeye göre belirlenmiştir. Çocukların "
            "reşit olması, destek süresinin sona ermesi gibi hallerde paylar, "
            "Yargıtay profiline uygun biçimde dinamik olarak güncellenmiştir."
        )
    elif ci.profile == ProfileType.EXPERT:
        return (
            "Destek paylarının eş, çocuk, anne ve baba arasında dağıtımında, "
            "bilirkişinin somut olayın özelliklerine göre belirlediği esnek profil "
            "kullanılmış; destek payları, aile yapısı, fiili destek ilişkisi ve "
            "ekonomik koşullar dikkate alınarak kişiselleştirilmiştir."
        )
    else:
        return (
            "Destek paylarının dağıtımında, aile içindeki fiili destek ilişkisini "
            "yansıtan ve doktrin ile içtihatla uyumlu bir profil esas alınmıştır."
        )


# ---------------------------------------------------------------------------
# 5) İSKONTO (TEKNİK FAİZ) AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_discount(ci: CalculationInput) -> str:
    """
    Hesapta kullanılan teknik faiz (rapor iskonto oranı) için açıklama.

    CalculationInput içinde alanın adı: report_discount_rate
    """
    # Eski sürümlerle uyum için getattr kullanıyoruz, yoksa 0.0 kabul edeceğiz
    r = getattr(ci, "report_discount_rate", 0.0)

    if r == 0 or abs(r) < 1e-6:
        return (
            "Destekten yoksun kalma zararı geleceğe yönelik olmakla birlikte, "
            "gelirlerdeki artışlar ile paranın zaman değeri ve enflasyonun "
            "birbirini yaklaşık dengeleyeceği varsayımına dayanılarak rapor "
            "iskonto oranı (teknik faiz) %0 alınmıştır. Bu durumda gelecekteki "
            "yıllık destek tutarları nominal olarak toplanarak bugünkü değer "
            "bulunmuştur. Bu yaklaşım, Yargıtay'ın bir kısım kararlarında "
            "benimsediği sıfır faizli hesap yöntemiyle uyumludur."
        )

    return (
        f"Destekten yoksun kalma zararı geleceğe yönelik bir zarar olduğundan, "
        f"ileride elde edilmesi beklenen yıllık destek payları rapor iskonto "
        f"oranı olarak kabul edilen %{r*100:.2f} teknik faiz üzerinden bugünkü "
        "değere indirgenmiştir. Böylece paranın zaman değeri ve muhtemel yatırım "
        "getirileri dikkate alınarak aktüeryal bir iskonto uygulanmıştır."
    )

# ---------------------------------------------------------------------------
# 6) SGK İNDİRİMİ AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_sgk(ci: CalculationInput) -> str:
    """
    SGK indirimi açıklaması.

    CalculationInput:
      - sgk_monthly_income : Aylık bağlanan gelir (varsa)
      - sgk_psd_factor     : Peşin sermaye değeri katsayısı (ör. 12)
      - sgk_deduction_type : NONE / HALF / FULL
    """
    # Aylık SGK geliri yoksa veya indirim tipi NONE ise
    if ci.sgk_deduction_type == SGKDeductionType.NONE or ci.sgk_monthly_income <= 0:
        return (
            "Sosyal Güvenlik Kurumu tarafından hak sahiplerine bağlanan aylık "
            "gelir bulunmadığından veya dosya kapsamındaki SGK ödemelerinin "
            "tazminattan indirilmemesi gerektiği değerlendirildiğinden, bu "
            "hesapta SGK indirimi uygulanmamıştır."
        )

    # Peşin sermaye değeri bu modelde: sgk_monthly_income * 12 * sgk_psd_factor
    # (bkz. sgk.compute_sgk_psd fonksiyonu)
    if ci.sgk_deduction_type == SGKDeductionType.FULL:
        return (
            "İşbu dosyada, iş kazası veya benzeri hallerde işverenin sorumluluğuna "
            "isabet eden kısım yönünden, Sosyal Güvenlik Kurumu tarafından "
            "bağlanan aylığın peşin sermaye değeri (yaklaşık olarak aylık gelir "
            "× 12 × katsayı) tam olarak tazminattan indirilmiştir. Böylece aynı "
            "zararın hem SGK hem de işveren tarafından mükerrer şekilde "
            "tazmin edilmesi önlenmiştir."
        )

    if ci.sgk_deduction_type == SGKDeductionType.HALF:
        return (
            "Bu dosyada SGK tarafından hak sahiplerine bağlanan aylığın peşin "
            "sermaye değeri (yaklaşık olarak aylık gelir × 12 × katsayı), "
            "Yargıtay uygulamasında üçüncü kişi sorumluluğuna isabet eden kısım "
            "yönünden benimsendiği üzere %50 oranında tazminattan indirilmiştir. "
            "Bu suretle hem sosyal güvenlik sisteminin koruma amacı hem de aynı "
            "zararın birden fazla kez tazmin edilmemesi ilkesi gözetilmiştir."
        )

    # Her ihtimale karşı emniyet metni
    return (
        "SGK ödemelerinin tazminat hesabına etkisi, dosya kapsamındaki belgeler "
        "ve sosyal güvenlik mevzuatı çerçevesinde değerlendirilmiş; uygun oran "
        "ve tutarda SGK indirimi uygulanmıştır."
    )

# ---------------------------------------------------------------------------
# 7) EVLENME İHTİMALİ (AYİM TABLOSU / MANUEL ORAN) AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_marriage_and_ayim(ci: CalculationInput) -> str:
    # models.py'de: apply_ayim: bool, eş için AYİM tablosu; ayrıca
    # assume_marriage_if_single parametreleri var.
    parts: List[str] = []

    if getattr(ci, "apply_ayim", False):
        parts.append(
            "Sağ kalan eş yönünden, genç yaşta dul kalma halinde yeniden evlenme "
            "olasılığının yüksek olduğu kabul edilerek, Askeri Yüksek İdare "
            "Mahkemesi içtihatlarında geliştirilen ve yaşa göre evlenme olasılığını "
            "gösteren AYİM tablosu esas alınmış; tazminattan bu tabloya uygun "
            "oranda evlenme indirimi yapılmıştır."
        )

    if getattr(ci, "assume_marriage_if_single", False):
        parts.append(
            "Destekçinin bekâr olması ve ilerleyen yaşlarda evlenmesinin hayatın "
            "olağan akışına uygun görülmesi nedeniyle, farazi evlilik ve çocuk "
            "varsayımları kullanılmış; belirlenen yaşta (örneğin "
            f"{getattr(ci, 'assumed_marriage_age', 25)} yaş) evleneceği ve belli "
            "yıllar içinde çocuk sahibi olacağı kabul edilerek, destek profili bu "
            "varsayımlara göre oluşturulmuştur."
        )

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# 8) YETİŞTİRME GİDERİ (TRAINING) AÇIKLAMASI
# ---------------------------------------------------------------------------

def explain_training(ci: CalculationInput) -> str:
    if not getattr(ci, "training_enabled", False):
        return ""
    rate = getattr(ci, "training_rate", 0.05)
    return (
        f"Dosyada, ölenin anne ve babası tarafından yetiştirilmesine ilişkin "
        f"yetiştirme giderleri de değerlendirilmiş; bu kapsamda, destekçinin "
        f"çocukluk döneminde yapılan zorunlu giderlerin tazminattan "
        f"{rate:.0%} oranında indirime konu edilmesi uygun görülmüştür. "
        "Bu indirim, yetiştirme giderlerinin bir kısmının destekçinin ölümüyle "
        "ilgili zararla ilişkilendirilmesi ve mükerrer tazminin önlenmesi "
        "amacını taşımaktadır."
    )


# ---------------------------------------------------------------------------
# 9) TOPLU PARAMETRE AÇIKLAMASI (RAPORDA KULLANIM)
# ---------------------------------------------------------------------------

def build_parameter_explanation(ci: CalculationInput) -> str:
    """
    Raporun 'Hukuki ve Teknik Esaslar' veya 'Varsayımlar' bölümünde kullanılmak üzere,
    o dosyada seçilmiş parametrelere göre otomatik açıklama metni üretir.
    """
    parts: List[str] = []

    # Yaşam tablosu
    parts.append(explain_life_table_choice(ci.life_table))

    # Gelir modu
    parts.append(explain_income_mode(ci))

    # Aktif/pasif dönem
    parts.append(explain_active_passive(ci))
    parts.append(explain_passive_income(ci))

    # Profil
    parts.append(explain_profile(ci))

    # İskonto
    parts.append(explain_discount(ci))

    # SGK
    parts.append(explain_sgk(ci))

    # Evlenme ihtimali / bekâr destek varsayımları
    marr_text = explain_marriage_and_ayim(ci)
    if marr_text:
        parts.append(marr_text)

    # Yetiştirme gideri
    tr_text = explain_training(ci)
    if tr_text:
        parts.append(tr_text)

    # Boş olmayan bölümleri iki satır boşlukla birleştir
    parts = [p for p in parts if p.strip()]
    return "\n\n".join(parts)
