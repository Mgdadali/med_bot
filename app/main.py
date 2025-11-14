import os
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters
)

import crud  # تمت مراجعة الربط

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# =========================
#     انتــلاق البــوت
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود!")

crud.init_db()

# =========================
#   دوال الواجهة الرئيسية
# =========================

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    keyboard = [
        [
            InlineKeyboardButton("📂 رفع محتوى جديد", callback_data="upload_menu"),
            InlineKeyboardButton("📥 عرض المحتوى", callback_data="view_menu")
        ]
    ]
    update.message.reply_text(
        "👋 أهلاً بك في نظام إدارة محتوى كلية الطب.\nاختر ما تريده:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
#   القائمة: رفع محتوى
# =========================

def upload_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id

    crud.set_waiting_file(chat_id, True)   # يجعل المستخدم في وضع انتظار ملف

    query.message.reply_text(
        "📤 أرسل الآن *الفيديو أو الملف* ليتم تسجيله.",
        parse_mode=None
    )


# =========================
#   استقبال ملف (فيديو أو PDF)
# =========================

def receive_file(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if not crud.is_waiting_file(chat_id):
        update.message.reply_text("❗ أرسل /start للبدء.")
        return

    file_id = None
    type_ = None

    if update.message.video:
        file_id = update.message.video.file_id
        type_ = "video"
    elif update.message.document:
        file_id = update.message.document.file_id
        type_ = "document"
    else:
        update.message.reply_text("❗ يجب إرسال فيديو أو ملف.")
        return

    crud.set_waiting_file_fileid(chat_id, file_id, type_)

    update.message.reply_text(
        "👨‍⚕️ أدخل *اسم الدكتور* المسؤول عن هذا المحتوى:",
        parse_mode=None
    )

# =========================
#    إدخال اسم الدكتور
# =========================

def receive_doctor(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if not crud.is_waiting_file(chat_id):
        return

    doctor = update.message.text.strip()
    crud.set_waiting_file_doctor(chat_id, doctor)

    keyboard = [
        [
            InlineKeyboardButton("Anatomy", callback_data="course_Anatomy"),
            InlineKeyboardButton("Histology", callback_data="course_Histology"),
        ],
        [
            InlineKeyboardButton("Biochemistry", callback_data="course_Biochemistry"),
            InlineKeyboardButton("Physiology", callback_data="course_Physiology")
        ]
    ]

    update.message.reply_text(
        f"✔ تم حفظ اسم الدكتور: {doctor}\nالآن اختر *المادة*: ",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
#     اختيار المادة
# =========================

def choose_course(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id

    course = query.data.replace("course_", "")
    context.user_data["course"] = course

    keyboard = [
        [
            InlineKeyboardButton("🎥 فيديو", callback_data="type_video"),
            InlineKeyboardButton("📘 مرجع", callback_data="type_reference"),
        ],
        [
            InlineKeyboardButton("📄 PDF", callback_data="type_pdf"),
        ]
    ]

    query.message.reply_text(
        f"📚 المادة: *{course}*\nاختر نوع المحتوى:",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
#     اختيار نوع المحتوى
# =========================

def choose_type(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id

    selected_type = query.data.replace("type_", "")
    course = context.user_data.get("course")

    waiting = crud.get_waiting_file(chat_id)

    if not waiting or not waiting.get("file_id"):
        query.message.reply_text("❌ لم يتم العثور على الملف. أعد إرسال الملف من البداية.")
        crud.set_waiting_file(chat_id, False)
        return

    doctor = waiting.get("doctor") or ""
    file_id = waiting.get("file_id")

    # حفظ الصف النهائي
    crud.add_material(course, selected_type, file_id, doctor)

    crud.set_waiting_file(chat_id, False)

    query.message.reply_text(
        "🎉 تم حفظ المحتوى بنجاح!\n"
        f"📚 المادة: {course}\n"
        f"📝 النوع: {selected_type}\n"
        f"👨‍⚕ الدكتور: {doctor}",
        parse_mode=None
    )


# =========================
#     عرض المحتوى
# =========================

def view_menu(update: Update, context: CallbackContext):
    query = update.callback_query

    keyboard = [
        [
            InlineKeyboardButton("Anatomy", callback_data="viewcourse_Anatomy"),
            InlineKeyboardButton("Histology", callback_data="viewcourse_Histology"),
        ],
        [
            InlineKeyboardButton("Biochemistry", callback_data="viewcourse_Biochemistry"),
            InlineKeyboardButton("Physiology", callback_data="viewcourse_Physiology")
        ]
    ]

    query.message.reply_text(
        "📥 اختر المادة لعرض محتوياتها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def view_course(update: Update, context: CallbackContext):
    query = update.callback_query
    course = query.data.replace("viewcourse_", "")

    keyboard = [
        [
            InlineKeyboardButton("🎥 فيديو", callback_data=f"viewtype_{course}_video"),
            InlineKeyboardButton("📘 مرجع", callback_data=f"viewtype_{course}_reference"),
        ],
        [
            InlineKeyboardButton("📄 PDF", callback_data=f"viewtype_{course}_pdf")
        ]
    ]

    query.message.reply_text(
        f"📚 اختر نوع المحتوى لمادة *{course}*:",
        parse_mode=None,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def view_type(update: Update, context: CallbackContext):
    query = update.callback_query
    _, course, type_ = query.data.split("_")

    materials = crud.get_materials(course, type_)

    if not materials:
        query.message.reply_text("❌ لا يوجد محتوى مسجل لهذا النوع.")
        return

    for item in materials:
        file_id = item["file_id"]
        doctor = item["doctor"]

        caption = f"👨‍⚕ {doctor}\n📚 {course}\n📝 {type_}"

        try:
            if type_ == "video":
                query.message.reply_video(file_id, caption=caption, parse_mode=None)
            else:
                query.message.reply_document(file_id, caption=caption, parse_mode=None)
        except Exception as e:
            query.message.reply_text(f"❌ خطأ أثناء عرض المحتوى: {e}")


# =========================
#       تشغيل البوت
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر رئيسية
    app.add_handler(CommandHandler("start", start))

    # رفع ملف
    app.add_handler(CallbackQueryHandler(upload_menu, pattern="upload_menu"))

    # لوحة عرض
    app.add_handler(CallbackQueryHandler(view_menu, pattern="view_menu"))

    # إرسال ملف
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, receive_file))

    # إدخال اسم الدكتور
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_doctor))

    # اختيار مادة
    app.add_handler(CallbackQueryHandler(choose_course, pattern="course_"))

    # اختيار نوع المحتوى (رفع)
    app.add_handler(CallbackQueryHandler(choose_type, pattern="type_"))

    # عرض
    app.add_handler(CallbackQueryHandler(view_course, pattern="viewcourse_"))
    app.add_handler(CallbackQueryHandler(view_type, pattern="viewtype_"))

    app.run_polling()


if __name__ == "__main__":
    main()
