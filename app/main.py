import os
import requests
import logging
from fastapi import FastAPI, Header, HTTPException
from app import crud

# ========= Logging مفصل =========
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ========= الإعدادات الأساسية =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN", None)
ADMIN_USERNAME = "@Mgdad_Ali"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="Med Faculty Bot")

@app.on_event("startup")
async def startup():
    crud.init_db()
    logger.info("✅ Database initialized successfully.")

# ========= إدارة رفع الملفات المتعددة للأدمن =========
UPLOAD_SESSION = {}  # keyed by chat_id -> {"semester":..., "course":..., "type":..., "files": [file_id1, file_id2, ...]}

# ========= حالة المستخدم لاختيار السمستر والمقرر والنوع =========
USER_STATE = {}  # keyed by chat_id -> {"semester": ..., "course": ..., "type": ...}

# ========= دوال مساعدة =========
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        logger.info(f"Send message status: {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.exception(f"Failed to send message: {e}")

def send_file(chat_id, file_id, content_type="pdf"):
    try:
        if content_type == "video":
            r = requests.post(f"{TELEGRAM_API}/sendVideo", json={"chat_id": chat_id, "video": file_id})
        else:
            r = requests.post(f"{TELEGRAM_API}/sendDocument", json={"chat_id": chat_id, "document": file_id})
        logger.info(f"Send file status: {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.exception(f"Failed to send file: {e}")

def is_admin(user):
    return user.get("username") == ADMIN_USERNAME.replace("@", "")

# ========= القوائم =========
def get_main_keyboard(is_admin=False):
    buttons = [[{"text": "ابدأ 🎓"}], [{"text": "تواصل مع المطور 👨‍💻"}]]
    if is_admin:
        buttons.append([{"text": "رفع ملف جديد 📤"}])
    return {"keyboard": buttons, "resize_keyboard": True}

def get_semesters_keyboard():
    return {
        "keyboard": [
            [{"text": "الفصل الأول 1️⃣"}, {"text": "الفصل الثاني 2️⃣"}],
            [{"text": "الفصل الثالث 3️⃣"}, {"text": "الفصل الرابع 4️⃣"}],
            [{"text": "الفصل الخامس 5️⃣"}, {"text": "الفصل السادس 6️⃣"}],
            [{"text": "الفصل السابع 7️⃣"}, {"text": "الفصل الثامن 8️⃣"}],
            [{"text": "الفصل التاسع 9️⃣"}, {"text": "الفصل العاشر 🔟"}],
            [{"text": "🏠 القائمة الرئيسية"}]
        ],
        "resize_keyboard": True
    }

def get_courses_keyboard(semester):
    # تحديد المقررات حسب كل سمستر
    courses_map = {
        "1": [
            [{"text": "🚧 المواد غير متوفرة حالياً"}]
        ],
        "2": [
            [{"text": "English"}, {"text": "Statistic"}],
            [{"text": "Nutrition"}, {"text": "Ethics"}],
            [{"text": "Embryology"}, {"text": "Computer"}]
        ],
        "3": [
            [{"text": "دراسات سودانية"}, {"text": "Community"}],
            [{"text": "Pathology"}, {"text": "musculoskeletal system"}]
        ],
        "4": [
            [{"text": "Primary Health Care"}],
            [{"text": "Cardiopulmonary"}, {"text": "Hematology"}]
        ],
        "5": [
            [{"text": "Primary Health Care"}, {"text": "Pharmacology"}],
            [{"text": "Endocrinology"}, {"text": "Cardiopulmonary"}]
        ],
        "6": [
            [{"text": "Gastrointestinal Tract"}]
        ],
        "7": [
            [{"text": "🚧 المواد غير متوفرة حالياً"}]
        ],
        "8": [
            [{"text": "🚧 المواد غير متوفرة حالياً"}]
        ],
        "9": [
            [{"text": "🚧 المواد غير متوفرة حالياً"}]
        ],
        "10": [
            [{"text": "🚧 المواد غير متوفرة حالياً"}]
        ]
    }
    
    course_buttons = courses_map.get(semester, [[{"text": "لا توجد مقررات"}]])
    course_buttons.append([{"text": "⬅️ رجوع"}, {"text": "🏠 القائمة الرئيسية"}])
    
    return {"keyboard": course_buttons, "resize_keyboard": True}

def get_types_keyboard(course):
    return {
        "keyboard": [
            [{"text": f"{course} 📄 PDF"}, {"text": f"{course} 🎥 فيديو"}],
            [{"text": f"{course} 📚 مرجع"}],
            [{"text": "⬅️ رجوع"}, {"text": "🏠 القائمة الرئيسية"}]
        ],
        "resize_keyboard": True
    }

def get_upload_finish_keyboard():
    return {
        "keyboard": [
            [{"text": "✅ انتهيت من الرفع"}],
            [{"text": "❌ إلغاء العملية"}]
        ],
        "resize_keyboard": True
    }

# ========= Webhook =========
@app.post("/webhook")
async def webhook(update: dict, x_telegram_bot_api_secret_token: str = Header(None)):
    try:
        if WEBHOOK_SECRET_TOKEN and x_telegram_bot_api_secret_token != WEBHOOK_SECRET_TOKEN:
            logger.warning("Invalid secret token received.")
            raise HTTPException(status_code=401, detail="Invalid secret header")

        logger.debug(f"Received update: {update}")
        msg = update.get("message")
        if not msg:
            return {"ok": True}

        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        user = msg.get("from", {})

        # التقاط الملفات
        file_info = None
        content_type = None
        if "document" in msg:
            file_info = msg["document"]
            content_type = "pdf"
        elif "video" in msg:
            file_info = msg["video"]
            content_type = "video"

        # ===== استقبال الملفات من الأدمن أثناء جلسة رفع نشطة =====
        if file_info and is_admin(user) and chat_id in UPLOAD_SESSION:
            session = UPLOAD_SESSION[chat_id]
            file_id = file_info.get("file_id")
            
            # تأكد من أن النوع متطابق
            if session.get("type") == content_type:
                session["files"].append(file_id)
                files_count = len(session["files"])
                send_message(
                    chat_id, 
                    f"✅ تم استلام الملف #{files_count}\n\n"
                    f"📊 إجمالي الملفات المستلمة: {files_count}\n\n"
                    f"يمكنك إرسال المزيد أو اضغط '✅ انتهيت من الرفع' للحفظ.",
                    reply_markup=get_upload_finish_keyboard()
                )
            else:
                send_message(chat_id, f"⚠️ نوع الملف غير متطابق! اخترت {session.get('type')} ولكن أرسلت {content_type}")
            
            return {"ok": True}

        # ===== زر "انتهيت من الرفع" - حفظ كل الملفات =====
        if text == "✅ انتهيت من الرفع" and is_admin(user) and chat_id in UPLOAD_SESSION:
            session = UPLOAD_SESSION[chat_id]
            semester = session.get("semester")
            course = session.get("course")
            ctype = session.get("type")
            files = session.get("files", [])
            
            if not files:
                send_message(chat_id, "⚠️ لم يتم رفع أي ملفات! أرسل الملفات أولاً.")
                return {"ok": True}
            
            # حفظ كل الملفات في قاعدة البيانات
            saved_count = 0
            for file_id in files:
                try:
                    crud.add_material(semester, course, ctype, file_id)
                    saved_count += 1
                except Exception as e:
                    logger.exception(f"Failed to save file {file_id}: {e}")
            
            # مسح الجلسة
            UPLOAD_SESSION.pop(chat_id, None)
            
            # رسالة تأكيد
            send_message(
                chat_id,
                f"✅ تم حفظ {saved_count} ملف بنجاح!\n\n"
                f"📚 السمستر: {semester}\n"
                f"📖 المقرر: {course}\n"
                f"📂 النوع: {ctype}",
                reply_markup=get_main_keyboard(is_admin=True)
            )
            return {"ok": True}

        # ===== زر "إلغاء العملية" =====
        if text == "❌ إلغاء العملية" and is_admin(user) and chat_id in UPLOAD_SESSION:
            UPLOAD_SESSION.pop(chat_id, None)
            send_message(chat_id, "❌ تم إلغاء عملية الرفع.", reply_markup=get_main_keyboard(is_admin=True))
            return {"ok": True}

        # ===== أوامر الأدمن =====
        if text == "رفع ملف جديد 📤" and is_admin(user):
            # بدء جلسة رفع جديدة
            UPLOAD_SESSION[chat_id] = {"semester": None, "course": None, "type": None, "files": []}
            send_message(chat_id, "📤 اختر السمستر الذي تريد رفع الملفات له:", reply_markup=get_semesters_keyboard())
            return {"ok": True}

        if text and text.startswith("/addfile") and is_admin(user):
            parts = text.split()
            if len(parts) == 5:
                semester, course, ctype, file_id = parts[1], parts[2], parts[3], parts[4]
                crud.add_material(semester, course, ctype, file_id)
                send_message(chat_id, f"✅ تمت إضافة {ctype} لمادة {course} (سمستر {semester}) بنجاح!")
            else:
                send_message(chat_id, "❌ الصيغة الصحيحة:\n/addfile <semester> <course> <type> <file_id>")
            return {"ok": True}

        # ===== أوامر المستخدم =====
        if text == "/start":
            USER_STATE.pop(chat_id, None)
            UPLOAD_SESSION.pop(chat_id, None)
            welcome_text = (
                "👋 مرحبًا بك في بوت كلية الطب – جامعة المناقل!\n\n"
                "📚 هذا البوت يساعدك للوصول إلى محتوى المقررات بسهولة.\n"
                "⚠️ تنويه: البوت في مراحل الصيانة لرفع كميات كبيرة من المواد.\n"
            )
            send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(is_admin(user)))
            return {"ok": True}

        if text == "تواصل مع المطور 👨‍💻":
            send_message(chat_id, f"📩 تواصل مع المطور: {ADMIN_USERNAME}")
            return {"ok": True}

        if text == "🏠 القائمة الرئيسية":
            USER_STATE.pop(chat_id, None)
            UPLOAD_SESSION.pop(chat_id, None)
            send_message(chat_id, "🏠 عدت إلى القائمة الرئيسية", reply_markup=get_main_keyboard(is_admin(user)))
            return {"ok": True}

        if text == "ابدأ 🎓":
            USER_STATE.pop(chat_id, None)
            send_message(chat_id, "📚 اختر الفصل الدراسي:", reply_markup=get_semesters_keyboard())
            return {"ok": True}

        if text == "⬅️ رجوع":
            state = USER_STATE.get(chat_id, {})
            
            # إذا كان عند اختيار النوع، نرجع لاختيار المقرر
            if state.get("course") and state.get("semester"):
                state.pop("type", None)
                state.pop("course", None)
                send_message(chat_id, f"⬅️ اختر المقرر:", reply_markup=get_courses_keyboard(state.get("semester")))
                return {"ok": True}
            
            # إذا كان عند اختيار المقرر، نرجع لاختيار السمستر
            if state.get("semester"):
                USER_STATE.pop(chat_id, None)
                send_message(chat_id, "⬅️ اختر الفصل الدراسي:", reply_markup=get_semesters_keyboard())
                return {"ok": True}
            
            # افتراضي: رجوع للسمسترات
            send_message(chat_id, "⬅️ اختر الفصل الدراسي:", reply_markup=get_semesters_keyboard())
            return {"ok": True}

        # ===== اختيار السمستر =====
        semester_map = {
            "الفصل الأول 1️⃣": "1",
            "الفصل الثاني 2️⃣": "2",
            "الفصل الثالث 3️⃣": "3",
            "الفصل الرابع 4️⃣": "4",
            "الفصل الخامس 5️⃣": "5",
            "الفصل السادس 6️⃣": "6",
            "الفصل السابع 7️⃣": "7",
            "الفصل الثامن 8️⃣": "8",
            "الفصل التاسع 9️⃣": "9",
            "الفصل العاشر 🔟": "10"
        }
        
        if text in semester_map:
            semester = semester_map[text]
            
            # للأدمن في جلسة رفع: حفظ السمستر
            if is_admin(user) and chat_id in UPLOAD_SESSION:
                UPLOAD_SESSION[chat_id]["semester"] = semester
                send_message(chat_id, f"✅ تم اختيار {text}. الآن اختر المقرر:", reply_markup=get_courses_keyboard(semester))
                return {"ok": True}
            
            # للمستخدم العادي: حفظ في USER_STATE
            USER_STATE[chat_id] = {"semester": semester}
            send_message(chat_id, f"📖 اختر المقرر من {text}:", reply_markup=get_courses_keyboard(semester))
            return {"ok": True}

        # ===== اختيار المقرر =====
        course_names = [
            # السمستر الثاني
            "English", "Statistic", "Nutrition", "Ethics", "Embryology", "Computer",
            # السمستر الثالث
            "دراسات سودانية", "Community", "Pathology", "musculoskeletal system",
            # السمستر الرابع
            "Primary Health Care", "Cardiopulmonary", "Hematology",
            # السمستر الخامس
            "Pharmacology", "Endocrinology",
            # السمستر السادس
            "Gastrointestinal Tract"
        ]

        if text in course_names:
            # للأدمن في جلسة رفع: حفظ المقرر
            if is_admin(user) and chat_id in UPLOAD_SESSION:
                UPLOAD_SESSION[chat_id]["course"] = text
                send_message(chat_id, f"📂 اختر نوع المحتوى لمقرر {text}:", reply_markup=get_types_keyboard(text))
                return {"ok": True}
            
            # للمستخدم: حفظ المقرر
            state = USER_STATE.get(chat_id, {})
            if not state.get("semester"):
                send_message(chat_id, "⚠️ يرجى اختيار السمستر أولاً")
                return {"ok": True}
            
            state["course"] = text
            USER_STATE[chat_id] = state
            send_message(chat_id, f"📂 اختر نوع المحتوى لمقرر {text}:", reply_markup=get_types_keyboard(text))
            return {"ok": True}

        # ===== اختيار نوع الملف =====
        if text and any(x in text for x in ["PDF", "فيديو", "مرجع"]):
            course_name = text.split()[0]
            ctype = "pdf" if "PDF" in text else "video" if "فيديو" in text else "reference"

            # للأدمن في جلسة رفع: حفظ النوع وانتظار الملفات
            if is_admin(user) and chat_id in UPLOAD_SESSION:
                session = UPLOAD_SESSION[chat_id]
                semester = session.get("semester")
                course = session.get("course") or course_name

                if not semester or not course:
                    send_message(chat_id, "❌ بيانات غير مكتملة. أعد العملية.")
                    return {"ok": True}

                session["type"] = ctype
                
                file_type_text = "PDF" if ctype == "pdf" else "فيديو" if ctype == "video" else "مرجع"
                send_message(
                    chat_id,
                    f"✅ تم اختيار: {file_type_text}\n\n"
                    f"📚 السمستر: {semester}\n"
                    f"📖 المقرر: {course}\n"
                    f"📂 النوع: {file_type_text}\n\n"
                    f"الآن أرسل الملفات ({file_type_text}) واحداً تلو الآخر.\n"
                    f"عند الانتهاء اضغط '✅ انتهيت من الرفع'",
                    reply_markup=get_upload_finish_keyboard()
                )
                return {"ok": True}

            # للمستخدم: عرض الملفات مباشرة
            state = USER_STATE.get(chat_id, {})
            semester = state.get("semester")
            course = state.get("course")
            
            if not semester or not course:
                send_message(chat_id, "⚠️ يرجى اختيار السمستر والمقرر أولاً")
                return {"ok": True}

            # جلب الملفات من قاعدة البيانات
            mats = crud.get_materials(semester, course, ctype, use_cache=True)
            
            if not mats:
                send_message(chat_id, f"🚧 لا توجد ملفات متاحة حالياً لـ {course} ({ctype})")
                return {"ok": True}
            
            send_message(chat_id, f"📤 جاري إرسال ملفات {course} ({ctype})...")
            for m in mats:
                send_file(chat_id, m.get("file_id"), content_type=ctype)
            
            return {"ok": True}

        # افتراضي
        send_message(chat_id, "🤔 لم أفهم الأمر، يرجى اختيار من القائمة.")
        return {"ok": True}

    except Exception as e:
        logger.exception(f"Exception in webhook processing: {e}")
        return {"ok": True}
