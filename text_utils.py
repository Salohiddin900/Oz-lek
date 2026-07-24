"""
Matnni "tushunishga" yordam beradigan modul:
  - Kirill yozuvini lotin yozuviga o'giradi (foydalanuvchi "Нимесил" deb yozsa ham tushunadi)
  - Kichik xatolarga (bitta-ikkita harf farqi) chidamli qidiruv qiladi
Hech qanday tashqi kutubxona kerak emas — Python'ning o'zidagi vositalar bilan ishlaydi.
"""

import difflib
import re

# O'zbekcha kirill -> lotin harflari mosligi (asosiy holatlar)
_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "қ": "q", "ғ": "g'", "ў": "o'", "ҳ": "h",
}


def _transliterate(text: str) -> str:
    result = []
    for ch in text.lower():
        result.append(_CYRILLIC_TO_LATIN.get(ch, ch))
    return "".join(result)


def normalize(text: str) -> str:
    """Kichik harflarga o'giradi, kirillni lotinlashtiradi, ortiqcha belgilarni tozalaydi."""
    text = _transliterate(text.strip().lower())
    text = re.sub(r"[^a-z0-9'\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(a: str, b: str) -> float:
    """0 dan 1 gacha o'xshashlik darajasi (1 = aynan bir xil)."""
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_best_medicine_matches(query: str, medicines: list, threshold: float = 0.55):
    """
    Dorilar ro'yxatidan so'rovga eng mos kelganlarini topadi.
    Aniq mos kelish (substring) bo'lsa ustuvor, bo'lmasa o'xshashlik darajasi bo'yicha.
    """
    norm_query = normalize(query)
    if not norm_query:
        return []

    scored = []
    for m in medicines:
        norm_name = normalize(m["name"])
        if norm_query in norm_name or norm_name in norm_query:
            score = 0.99  # substring moslik — eng ishonchli
        else:
            score = similarity(norm_query, norm_name)
        if score >= threshold:
            scored.append((score, m))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [m for _, m in scored]


_COMPANY_KEYWORDS = ["oz-lek", "ozlek", "oz lek", "kompaniya", "haqida", "firma", "shirkat", "malumot"]


def is_company_query(text: str) -> bool:
    """Matn 'Oz-Lek haqida' so'roviga o'xshaydimi — kichik xatolarni ham kechiradi."""
    norm_text = normalize(text)
    words = norm_text.split()
    for keyword in _COMPANY_KEYWORDS:
        norm_keyword = normalize(keyword)
        if norm_keyword in norm_text:
            return True
        for word in words:
            if similarity(word, norm_keyword) >= 0.75:
                return True
    return False
