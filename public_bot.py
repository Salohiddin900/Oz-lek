"""
Mijozlar uchun bot. Vazifalari:

1) "Oz-Lek haqida" — matn tugmasi orqali ham, ovozli xabar orqali ham so'rasa bo'ladi.
   Kichik yozuv xatolari va "Oz-Lek", "OzLek", "oz lek" kabi turli yozilishlar tushuniladi.

2) Dorilar katalogi — /start bosilganda menyu chiqadi (admin panelga qo'shilgan dorilar).
   Dori nomini bosib yoki o'zi yozib so'rasa bo'ladi. Bunda:
     - Kirill yozuvida yozilsa ham tushunadi ("Нимесил" -> "Nimesil")
     - Kichik xatolar (bitta-ikkita harf farqi, katta-kichik harf) kechiriladi
     - Hech qanday moslik topilmasa — "bunday dori yo'q" deb aniq javob beradi

Ovozli so'rovni tanish uchun Google Speech Recognition ishlatiladi (uz-UZ tili).
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
import text_utils
from config import PUBLIC_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💊 Dorilar katalogi")],
        [KeyboardButton(text="ℹ️ Oz-Lek haqida")],
    ],
    resize_keyboard=True,
)


def medicines_keyboard():
    medicines = db.list_medicines()
    buttons = [
        [InlineKeyboardButton(text=m["name"], callback_data=f"med_{m['id']}")]
        for m in medicines
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_medicine(m: dict) -> str:
    return f"<b>{m['name']}</b>\n\n{m['description']}"


async def send_medicine(message: Message, m: dict):
    caption = format_medicine(m)
    if m["photo_file_id"]:
        await message.answer_photo(m["photo_file_id"], caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Assalomu alaykum! Oz-Lek rasmiy botiga xush kelibsiz.\n\n"
        "💊 Dorilar katalogi — mavjud dorilarni ko'rish\n"
        "ℹ️ Oz-Lek haqida — kompaniya haqida ma'lumot\n\n"
        "Istalgan dori nomini shunchaki yozib yuborishingiz yoki ovozli xabar bilan so'rashingiz ham mumkin.",
        reply_markup=MAIN_MENU,
    )


# ---------- Kompaniya haqida ----------

@router.message(F.text == "ℹ️ Oz-Lek haqida")
async def company_info_text(message: Message):
    await message.answer(db.get_company_info())


@router.message(F.voice)
async def company_info_voice(message: Message, bot: Bot):
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

    await message.answer(f"🗣 Eshitdim: <i>{text}</i>", parse_mode="HTML")
    await route_text_query(message, text)


# ---------- Dorilar katalogi ----------

@router.message(F.text == "💊 Dorilar katalogi")
async def catalog(message: Message):
    medicines = db.list_medicines()
    if not medicines:
        await message.answer("Hozircha dorilar ro'yxati bo'sh.")
        return
    await message.answer("Kerakli dorini tanlang yoki nomini yozib yuboring:", reply_markup=medicines_keyboard())


@router.callback_query(F.data.startswith("med_"))
async def show_medicine(call: CallbackQuery):
    medicine_id = int(call.data.split("_")[1])
    medicine = db.get_medicine(medicine_id)
    await call.answer()
    if not medicine:
        await call.message.answer("Bu dori topilmadi (o'chirilgan bo'lishi mumkin).")
        return
    await send_medicine(call.message, medicine)


async def route_text_query(message: Message, text: str):
    """
    Erkin matn/ovozdan kelgan so'rovni yo'naltiradi:
      1) Kompaniya haqida so'rovmi? (kichik xatolarga chidamli)
      2) Dori nomimi? (kirill/lotin, kichik xatolarga chidamli)
      3) Hech biriga mos kelmasa -> aniq "topilmadi" javobi
    """
    if text_utils.is_company_query(text):
        await message.answer(db.get_company_info())
        return

    medicines = db.list_medicines()
    matches = text_utils.find_best_medicine_matches(text, medicines)

    if not matches:
        await message.answer(
            f"❌ \"{text}\" nomli dori topilmadi.\n\n"
            "Iltimos, nomini tekshirib qayta yozing yoki '💊 Dorilar katalogi' tugmasi orqali ro'yxatdan tanlang."
        )
        return

    if len(matches) == 1:
        await send_medicine(message, matches[0])
    else:
        # Bir nechta yaqin moslik topilsa - tanlash uchun ro'yxat beramiz
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=m["name"], callback_data=f"med_{m['id']}")] for m in matches[:8]
        ])
        await message.answer("Bir nechta yaqin natija topildi, birini tanlang:", reply_markup=keyboard)


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
