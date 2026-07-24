"""
Bu fayl faqat MIJOZLAR botini ishga tushiradi.
Railway'da alohida servis sifatida shu faylni ishga tushiramiz,
shunda admin bot bilan bir vaqtda, lekin alohida ishlaydi.
"""

import asyncio
from public_bot import run_public_bot

if __name__ == "__main__":
    asyncio.run(run_public_bot())
