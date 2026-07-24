import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")
PUBLIC_BOT_TOKEN = os.getenv("PUBLIC_BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
PORT = int(os.getenv("PORT", "8000"))
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

if not ADMIN_BOT_TOKEN or not PUBLIC_BOT_TOKEN or not ADMIN_CHAT_ID:
    print("OGOHLANTIRISH: .env faylida ADMIN_BOT_TOKEN / PUBLIC_BOT_TOKEN / ADMIN_CHAT_ID to'liq emas!")
