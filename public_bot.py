"""
Mijozlar uchun bot (admin panel EMAS — bu alohida, mustaqil bot).

Vazifalari:
1) "Oz-Lek haqida" — matn tugmasi orqali ham, ovozli xabar orqali ham so'rasa bo'ladi.
2) Dorilar katalogi — /start bosilganda admin panelga kiritilgan dorilar menyusi chiqadi.
   Nomini bossa yoki o'zi yozib yuborsa (hatto kichik xato bilan yoki kirillcha yozsa ham),
   admin kiritgan rasm + tavsif chiqadi. Topilmasa — "bunday dori yo'q" deb aniq javob beradi.

Kril alifbosi va kichik imlo xatolari text_match.py moduli orqali qo'llab-quvvatlanadi.
Ovozli so'rov Google Speech Recognition orqali (uz-UZ) tanib olinadi.
Server (Railway)da ffmpeg o'rnatilgan bo'lishi kerak (pydub shuni talab qiladi).
"""

import logging
import os
import tempfile

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)

import database as db
from config import PUBLIC_BOT_TOKEN
from text_match import find_matching_medicines, is_company_info_query, is_generic_info_query

logging.basicConfig(level=logging.INFO)

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💊 Dorilar katalogi")],
        [KeyboardButton(text="ℹ️ Oz-Lek haqida")],
    ],
    resize_keyboard=True,
)


def medicines_keyboard(medicines=None):
    medicines = medicines if medicines is not None else db.list_medicines()
    buttons = [
        [InlineKeyboardButton(text=m["name"], callback_data=f"med_{m['id']}")]
        for m in medicines
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Assalomu alaykum! Oz-Lek rasmiy botiga xush kelibsiz.\n\n"
        "💊 Dorilar katalogi — mavjud dorilarni ko'rish\n"
        "ℹ️ Oz-Lek haqida — kompaniya haqida ma'lumot\n\n"
        "Istalgan dori nomini to'g'ridan-to'g'ri yozib yoki ovozli xabar yuborib ham so'rashingiz mumkin.",
        reply_markup=MAIN_MENU,
    )


# ---------- Kompaniya haqida ----------

@router.message(F.text == "ℹ️ Oz-Lek haqida")
async def company_info_button(message: Message):
    await message.answer(db.get_company_info())


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    """Ovozli xabarni matnga o'giradi va so'rovga mos javob beradi."""
    await message.answer("🎧 Ovozli xabaringiz tinglanmoqda...")

    try:
        import speech_recognition as sr
        from pydub import AudioSegment

        file = await bot.get_file(message.voice.file_id)
        with tempfile.TemporaryDirectory() as tmpdir:
            ogg_path = os.path.join(tmpdir, "voice.ogg")
            wav_path = os.path.join(tmpdir, "voice.wav")
            await bot.download_file(file.file_path, ogg_path)

            AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)

            text = recognizer.recognize_google(audio, language="uz-UZ")
    except Exception as e:
        logging.warning(f"Ovozni tanib bo'lmadi: {e}")
        await message.answer(
            "Kechirasiz, ovozingizni tushuna olmadim 😔\n"
            "Iltimos, matn orqali yozib ko'ring yoki '💊 Dorilar katalogi' / 'ℹ️ Oz-Lek haqida' tugmasidan foydalaning."
        )
        return

    await route_text_query(message, text)


# ---------- Dorilar katalogi ----------

@router.message(F.text == "💊 Dorilar katalogi")
async def catalog(message: Message):
    medicines = db.list_medicines()
    if not medicines:
        await message.answer("Hozircha dorilar ro'yxati bo'sh.")
        return
    await message.answer("Kerakli dorini tanlang yoki nomini yozib yuboring:", reply_markup=medicines_keyboard(medicines))


@router.callback_query(F.data.startswith("med_"))
async def show_medicine(call: CallbackQuery):
    medicine_id = int(call.data.split("_")[1])
    medicine = db.get_medicine(medicine_id)
    await call.answer()
    if not medicine:
        await call.message.answer("Bu dori topilmadi (o'chirilgan bo'lishi mumkin).")
        return
    caption = f"<b>{medicine['name']}</b>\n\n{medicine['description']}"
    if medicine["photo_file_id"]:
        await call.message.answer_photo(medicine["photo_file_id"], caption=caption, parse_mode="HTML")
    else:
        await call.message.answer(caption, parse_mode="HTML")


async def route_text_query(message: Message, raw_text: str):
    """
    Erkin matn yoki ovozdan kelgan so'rovni 'kompaniya haqida' yoki 'dori nomi' ga
    yo'naltiradi. Kirillcha yozuvni va kichik imlo xatolarini text_match.py orqali
    tushunadi.

    FIX (tartib o'zgartirildi):
    Avvalgi versiyada is_company_info_query() ENG BIRINCHI tekshirilardi va u
    "haqida"/"malumot" so'zlarining o'zi asosida ishlagani uchun "Parasetamol
    haqida ma'lumot bormi" kabi DORI haqidagi so'rovlar ham xato ravishda
    "kompaniya haqida" deb javob berilardi.

    Endi tartib:
      1) Aniq brend so'rovi (masalan "Oz-Lek haqida", "firma haqida") — darhol
         kompaniya ma'lumoti.
      2) Dori qidiruvi — agar mos dori(lar) topilsa, ular ko'rsatiladi.
      3) Faqat shundan keyin, hech qanday dori topilmasa VA matnda umumiy
         "haqida"/"malumot" so'zi bo'lsa — kompaniya ma'lumotiga fallback.
      4) Aks holda — "bunday dori yo'q".
    """

    # 1) Brend nomiga aniq ishora (masalan "Oz-Lek haqida ayting")
    if is_company_info_query(raw_text):
        await message.answer(db.get_company_info())
        return

    # 2) Dori qidiruvi — bu endi generic "haqida" tekshiruvidan OLDIN bajariladi
    all_medicines = db.list_medicines()
    results = find_matching_medicines(raw_text, all_medicines)

    if results:
        if len(results) == 1:
            m = results[0]
            caption = f"<b>{m['name']}</b>\n\n{m['description']}"
            if m["photo_file_id"]:
                await message.answer_photo(m["photo_file_id"], caption=caption, parse_mode="HTML")
            else:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer("Bir nechta natija topildi, birini tanlang:", reply_markup=medicines_keyboard(results))
        return

    # 3) Dori topilmadi — endi umumiy "haqida/malumot" so'ziga fallback qilamiz
    if is_generic_info_query(raw_text):
        await message.answer(db.get_company_info())
        return

    # 4) Hech narsa mos kelmadi
    await message.answer(
        f"❌ \"{raw_text}\" nomli dori topilmadi.\n"
        "Bunday dori yo'q, yoki nomini boshqacha yozib ko'ring, "
        "yoki '💊 Dorilar katalogi' tugmasidan tanlang."
    )


@router.message(F.text)
async def free_text(message: Message):
    """Foydalanuvchi tugmalardan tashqari, erkin nom yozganda ishlaydi."""
    await route_text_query(message, message.text)


async def run_public_bot():
    db.init_db()
    bot = Bot(token=PUBLIC_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
