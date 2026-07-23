"""
Foydalanuvchi yozgan yoki gapirgan matnni:
  1) kril alifbosidan lotinga o'giradi (agar kerak bo'lsa)
  2) kichik imlo xatolarini kechiradi (fuzzy matching)
orqali dorilar bazasidagi nomlar va "kompaniya haqida" so'zlari bilan solishtiradi.
"""
import difflib

CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
APOSTROPHES = ["'", "'", "`", "ʻ", "ʼ", "'"]

# FIX: "haqida" / "malumot" kabi umumiy so'zlar BREND nomisiz kelsa,
# bu ko'pincha "<dori> haqida ma'lumot" degani bo'ladi — kompaniya emas.
# Shuning uchun ularni ikkiga ajratamiz:
#   BRAND_KEYWORDS  - aniq "Oz-Lek" ga ishora qiladi, yolg'iz o'zi yetarli
#   GENERIC_KEYWORDS - faqat yordamchi so'z, yolg'iz holda ishlatilmaydi
BRAND_KEYWORDS = ["oz-lek", "oz lek", "ozlek", "firma", "shirkat", "korxona"]
GENERIC_KEYWORDS = ["kompaniya", "haqida", "malumot", "ma'lumot"]


def normalize(text: str) -> str:
    """Matnni kichik harfga o'tkazadi, krildan lotinga o'giradi, apostroflarni tozalaydi."""
    if not text:
        return ""
    text = text.lower().strip()
    text = "".join(CYR_TO_LAT.get(ch, ch) for ch in text)
    for ap in APOSTROPHES:
        text = text.replace(ap, "")
    text = " ".join(text.split())  # ortiqcha bo'shliqlarni olib tashlash
    return text


def find_matching_medicines(query: str, medicines: list, cutoff: float = 0.6, max_results: int = 5) -> list:
    """
    Dorilar ro'yxatidan so'rovga mos keladiganlarni topadi.
    Avval to'g'ridan-to'g'ri (qisman) moslikni, topilmasa — imlo xatolariga chidamli
    fuzzy qidiruvni qo'llaydi.
    """
    norm_query = normalize(query)
    if not norm_query:
        return []

    # 1) Qisman moslik (substring) — ikkala yo'nalishda:
    #    - so'rov nom ichida ("aspirin" -> "Aspirin Cardio")
    #    - nom so'rov ichida ("menga aspirin kerak" -> "Aspirin")
    direct = [
        m for m in medicines
        if norm_query in normalize(m["name"]) or normalize(m["name"]) in norm_query
    ]
    if direct:
        return direct

    # 2) Fuzzy qidiruv — kichik imlo xatolarini kechiradi
    norm_to_medicine = {normalize(m["name"]): m for m in medicines}
    close_names = difflib.get_close_matches(norm_query, norm_to_medicine.keys(), n=max_results, cutoff=cutoff)
    if close_names:
        return [norm_to_medicine[n] for n in close_names]

    # 3) So'z-so'z fuzzy solishtirish (masalan ko'p so'zli nomlar/gaplar uchun)
    results = []
    for m in medicines:
        norm_name = normalize(m["name"])
        ratio = difflib.SequenceMatcher(None, norm_query, norm_name).ratio()
        if ratio >= cutoff:
            results.append(m)
    return results


def is_company_info_query(text: str) -> bool:
    """
    Matn 'Oz-Lek haqida' turidagi so'rov ekanini tekshiradi.

    FIX: avvalgi versiyada "haqida"/"malumot" so'zlarining o'zi yetarli edi —
    bu "Parasetamol haqida ma'lumot bormi" kabi DORI haqidagi so'rovlarni ham
    noto'g'ri "kompaniya haqida" deb aniqlab yuborardi.

    Endi:
      - Agar brend nomi (oz-lek/firma/shirkat...) bo'lsa — darhol True.
      - Agar faqat umumiy so'z (haqida/malumot/kompaniya) bo'lsa — bu yetarli
        emas; chaqiruvchi kod (route_text_query) buni FAQAT hech qanday dori
        topilmagandan keyin, fallback sifatida tekshirishi kerak.
    """
    norm = normalize(text)
    if not norm:
        return False

    for kw in BRAND_KEYWORDS:
        if normalize(kw) in norm:
            return True

    for word in norm.split():
        for kw in BRAND_KEYWORDS:
            if difflib.SequenceMatcher(None, word, normalize(kw)).ratio() >= 0.8:
                return True
    return False


def is_generic_info_query(text: str) -> bool:
    """
    Faqat umumiy so'zlar ('haqida', 'malumot', 'kompaniya') asosida tekshiradi.
    route_text_query ichida FAQAT dori topilmaganda fallback sifatida chaqiriladi —
    shu tufayli "Parasetamol haqida" endi to'g'ri dori sifatida ishlanadi, chunki
    dori qidiruvi bu tekshiruvdan OLDIN bajariladi.
    """
    norm = normalize(text)
    if not norm:
        return False
    for kw in GENERIC_KEYWORDS:
        if normalize(kw) in norm:
            return True
    return False
