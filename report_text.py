# report_text.py
from __future__ import annotations

from typing import Dict, List, Set

from models import CalculationInput, CalculationResult, ProfileType
from legal_loader import LegalRepository, LegalSnippet
from topics import Topic, TOPIC_TAGS, determine_active_topics


def _profil_matches(snippet: LegalSnippet, profile: ProfileType) -> bool:
    """
    profil alanı:
      - "Ortak"  -> her profilde kullanılabilir
      - "Yargıtay" -> sadece Yargıtay profilinde
      - "Bilirkişi" -> sadece Bilirkişi profilinde
    """
    p = snippet.profil.lower()
    if p == "ortak":
        return True
    if p == "yargıtay" and profile == ProfileType.YARGITAY:
        return True
    if p in ("bilirkisi", "bilirkişi") and profile == ProfileType.EXPERT:
        return True
    # Bilinmeyen değerleri şimdilik ortak gibi düşünebiliriz
    if p not in ("ortak", "yargıtay", "bilirkisi", "bilirkişi"):
        return True
    return False


def select_snippets_for_topics(
    repo: LegalRepository,
    topics: Set[Topic],
    profile: ProfileType,
    max_per_topic: int = 2,
) -> Dict[Topic, List[LegalSnippet]]:
    """
    Her topic için, ilgili tag'lere sahip snippet'leri repository'den seçer.
    Profil filtresi uygular, priority'ye göre sıralar.
    max_per_topic ile sınırlandırır.
    """
    result: Dict[Topic, List[LegalSnippet]] = {}

    for topic in topics:
        tags = TOPIC_TAGS.get(topic, [])
        candidates: List[LegalSnippet] = []
        for tag in tags:
            for sn in repo.find_by_tag(tag):
                if sn in candidates:
                    continue
                if not _profil_matches(sn, profile):
                    continue
                candidates.append(sn)

        # priority sırası zaten loader'da tag bazında var ama burada da tekrar sort edebiliriz
        candidates.sort(key=lambda s: s.priority)
        if max_per_topic > 0:
            candidates = candidates[:max_per_topic]
        if candidates:
            result[topic] = candidates

    return result


def build_legal_explanation_text(
    ci: CalculationInput,
    res: CalculationResult,
    repo: LegalRepository,
) -> str:
    """
    Hesaplama parametrelerine göre etkin topic'leri bulur,
    uygun snippet'leri seçer ve basit bir 'Hukuki ve Teknik Esaslar' metni oluşturur.
    Şimdilik deterministik; ileride hibrit (LLM cila) katmanını bunun üstüne koyacağız.
    """
    topics = determine_active_topics(ci, res)
    selected = select_snippets_for_topics(repo, topics, ci.profile)

    # Bölümleri kabaca sıralamak için bir topic sırası
    order = [
        Topic.TRH2010,
        Topic.PMF1931,
        Topic.DONEM_ESASI,
        Topic.AKTIF_PASIF_TANIM,
        Topic.PASIF_MIN_ASGARI,
        Topic.PASIF_ORAN,
        Topic.ASKERLIK,
        Topic.YETISTIRME_GIDERI,
        Topic.AYIM_EVLI_ES,
        Topic.ANNE_BABA_AYRI_HAVUZ,
        Topic.ANNE_BABA_25_SINIRI,
        Topic.ANNE_BABA_YARIM_PAY,
        Topic.BEKAR_EV_COCUK_SENARYO,
        Topic.SGK_PSD,
        Topic.SGK_PSD_INDIRIM_TURU,
        Topic.AGI_2008_2021,
        Topic.AGI_2022_SONRASI_ISTISNA,
        Topic.KUSUR_ORANI,
        Topic.RAPOR_ISKONTO,
        Topic.YARGITAY_MODU,
        Topic.BILIRKISI_MODU,
    ]

    paragraphs: List[str] = []
    paragraphs.append("I. HUKUKİ VE TEKNİK ESASLAR\n")

    for topic in order:
        snippets = selected.get(topic)
        if not snippets:
            continue
        for sn in snippets:
            # Başlığı da metne dahil ediyoruz
            if sn.title:
                paragraphs.append(f"{sn.title}\n{sn.text}\n")
            else:
                paragraphs.append(f"{sn.text}\n")

    return "\n".join(paragraphs).strip()
