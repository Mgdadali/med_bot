# app/main.py
import os
import requests
from fastapi import FastAPI, Request, Header, HTTPException
from app.db import init_db
from app import crud

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", None)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="Med Faculty Bot")

@app.on_event("startup")
async def startup():
    init_db()

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def send_file(chat_id, file_id):
    requests.post(f"{TELEGRAM_API}/sendDocument", json={"chat_id": chat_id, "document": file_id})

@app.post("/webhook")
async def webhook(update: dict, x_telegram_bot_api_secret_token: str = Header(None)):
    if WEBHOOK_SECRET_TOKEN and x_telegram_bot_api_secret_token != WEBHOOK_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid secret header")

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            buttons = {
                "keyboard": [[{"text": "ابدأ 🎓"}]],
                "resize_keyboard": True
            }
            send_message(chat_id, "مرحبًا بك في *بوت كلية الطب – جامعة المناقل!* 👋\nاختر 'ابدأ' للمتابعة.", reply_markup=buttons)
            return {"ok": True}

        elif text == "ابدأ 🎓":
            buttons = {
                "keyboard": [
                    [{"text": "📘 التشريح"}, {"text": "🧠 الفسيولوجي"}],
                    [{"text": "🏠 القائمة الرئيسية"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, "اختر المقرر الدراسي:", reply_markup=buttons)

        elif text in ["📘 التشريح", "🧠 الفسيولوجي"]:
            course = "تشريح" if "التشريح" in text else "فسيولوجي"
            buttons = {
                "keyboard": [
                    [{"text": f"{course} 📄 PDF"}, {"text": f"{course} 🎥 فيديو"}, {"text": f"{course} 📚 مرجع"}],
                    [{"text": "🏠 القائمة الرئيسية"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, f"اختر نوع المحتوى لمقرر *{course}*:", reply_markup=buttons)

        elif "PDF" in text or "فيديو" in text or "مرجع" in text:
            # استخراج المقرر والنوع
            parts = text.split()
            course_name = parts[0]
            if "PDF" in text:
                content_type = "pdf"
            elif "فيديو" in text:
                content_type = "video"
            else:
                content_type = "reference"

            mat = crud.get_material(course_name, content_type)
            if mat and mat.file_id:
                send_message(chat_id, f"جارٍ إرسال {content_type} الخاص بمقرر {course_name}...")
                send_file(chat_id, mat.file_id)
            else:
                send_message(chat_id, "لم يتم العثور على هذا المحتوى بعد 🚧")

        elif text == "🏠 القائمة الرئيسية":
            buttons = {
                "keyboard": [[{"text": "ابدأ 🎓"}]],
                "resize_keyboard": True
            }
            send_message(chat_id, "عدت إلى القائمة الرئيسية 🏠", reply_markup=buttons)

    return {"ok": True}
