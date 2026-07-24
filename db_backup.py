"""
Bazani (oz_lek.db) alohida, maxfiy GitHub repo'ga avtomatik zaxira qiladi
va server qayta ishga tushganda o'sha yerdan tiklaydi.

Railway Volume yoki boshqa pullik xizmat kerak emas — faqat GitHub (bepul).

Kerakli muhit o'zgaruvchilari (Railway Variables):
  GITHUB_TOKEN  — Personal Access Token ('repo' ruxsati bilan)
  GITHUB_REPO   — masalan "salolodin-arch/oz-lek-data"
  GITHUB_BRANCH — odatda "main"
"""

import os
import base64
import logging
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
DB_FILE_NAME = "oz_lek.db"

_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def _api_url() -> str:
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILE_NAME}"


def is_configured() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def pull_from_github(local_path: str = DB_FILE_NAME):
    """Server ishga tushganda bazani GitHub'dan tiklaydi (agar u yerda mavjud bo'lsa)."""
    if not is_configured():
        logging.warning("GITHUB_TOKEN / GITHUB_REPO sozlanmagan — GitHub zaxirasi ISHLAMAYDI. "
                         "Ma'lumotlar har qayta deployda o'chib ketishi mumkin!")
        return
    try:
        resp = requests.get(_api_url(), headers=_HEADERS, params={"ref": GITHUB_BRANCH}, timeout=15)
        if resp.status_code == 200:
            content = resp.json()["content"]
            data = base64.b64decode(content)
            with open(local_path, "wb") as f:
                f.write(data)
            logging.info("✅ Baza GitHub'dagi zaxiradan tiklandi.")
        elif resp.status_code == 404:
            logging.info("GitHub'da hali zaxira yo'q — bo'sh baza bilan boshlanadi (bu birinchi ishga tushish uchun normal).")
        else:
            logging.warning(f"GitHub'dan tiklashda xato: {resp.status_code} {resp.text}")
    except Exception as e:
        logging.warning(f"GitHub'dan tiklashda xatolik: {e}")


def push_to_github(local_path: str = DB_FILE_NAME):
    """Har qanday o'zgarishdan keyin (dori qo'shildi/o'zgardi/o'chdi) bazani GitHub'ga saqlaydi."""
    if not is_configured():
        return
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()

        sha = None
        get_resp = requests.get(_api_url(), headers=_HEADERS, params={"ref": GITHUB_BRANCH}, timeout=15)
        if get_resp.status_code == 200:
            sha = get_resp.json()["sha"]

        payload = {
            "message": "Baza avtomatik yangilandi",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(_api_url(), headers=_HEADERS, json=payload, timeout=15)
        if put_resp.status_code not in (200, 201):
            logging.warning(f"GitHub'ga saqlashda xato: {put_resp.status_code} {put_resp.text}")
    except Exception as e:
        logging.warning(f"GitHub'ga saqlashda xatolik: {e}")
