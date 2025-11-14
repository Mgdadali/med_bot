import os
import threading
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 🔒 قفل لتفادي التداخل بين الطلبات
LOCK = threading.Lock()

# ===== إعداد Google Sheets =====
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "MedBot Files")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ متغير البيئة GOOGLE_SERVICE_ACCOUNT_JSON غير موجود!")

creds_info = json.loads(SERVICE_ACCOUNT_JSON)
credentials = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client = gspread.authorize(credentials)

# ===== تهيئة الورقة =====
def init_db():
    with LOCK:
        try:
            try:
                spreadsheet = client.open(GOOGLE_SHEET_NAME)
            except gspread.SpreadsheetNotFound:
                spreadsheet = client.create(GOOGLE_SHEET_NAME)

            sheet_titles = [s.title for s in spreadsheet.worksheets()]

            # materials: كل صف ملف واحد: course | type | file_id | doctor | created_at
            if "materials" not in sheet_titles:
                spreadsheet.add_worksheet(title="materials", rows=5000, cols=6)
                sheet = spreadsheet.worksheet("materials")
                sheet.append_row(["course", "type", "file_id", "doctor", "created_at"])
            else:
                sheet = spreadsheet.worksheet("materials")
                # تأكد أن العناوين تحتوي على doctor و created_at (إذا ورقة قديمة)
                header = sheet.row_values(1)
                expected = ["course", "type", "file_id", "doctor", "created_at"]
                if header[: len(expected)] != expected:
                    # إضافة رؤوس جديدة بطريقة بسيطة (لن نحذف بيانات قديمة) — فقط إذا كان صفر أو مختلف
                    try:
                        sheet.delete_rows(1)
                    except Exception:
                        pass
                    sheet.insert_row(expected, 1)

            # waiting_files: chat_id | file_id | type | doctor (doctor قد تملأ لاحقًا)
            if "waiting_files" not in sheet_titles:
                spreadsheet.add_worksheet(title="waiting_files", rows=1000, cols=4)
                sheet2 = spreadsheet.worksheet("waiting_files")
                sheet2.append_row(["chat_id", "file_id", "type", "doctor"])
            else:
                sheet2 = spreadsheet.worksheet("waiting_files")
                header2 = sheet2.row_values(1)
                if header2[:4] != ["chat_id", "file_id", "type", "doctor"]:
                    try:
                        sheet2.delete_rows(1)
                    except Exception:
                        pass
                    sheet2.insert_row(["chat_id", "file_id", "type", "doctor"], 1)

            print("✅ Google Sheet جاهز للاستخدام")

        except Exception as e:
            print(f"❌ خطأ أثناء التهيئة: {e}")


# ========== مواد دائمة ==========

def add_material(course, type_, file_id, doctor=None):
    """
    تضيف صفًا جديدًا في ورقة materials = كل ملف صف منفصل.
    """
    with LOCK:
        try:
            sheet = client.open(GOOGLE_SHEET_NAME).worksheet("materials")
            created_at = datetime.utcnow().isoformat()
            sheet.append_row([course, type_, file_id, doctor or "", created_at])
        except Exception as e:
            print(f"❌ خطأ أثناء إضافة المادة: {e}")


def get_materials(course, type_):
    """
    ترجع قائمة من الصفوف (كل عنصر dict) للمادة والنوع.
    """
    with LOCK:
        try:
            sheet = client.open(GOOGLE_SHEET_NAME).worksheet("materials")
            rows = sheet.get_all_records()
            results = [
                {"course": row.get("course"), "type": row.get("type"),
                 "file_id": row.get("file_id"), "doctor": row.get("doctor"),
                 "created_at": row.get("created_at")}
                for row in rows
                if str(row.get("course")) == str(course) and str(row.get("type")) == str(type_)
            ]
            return results
        except Exception as e:
            print(f"❌ خطأ أثناء البحث عن المادة: {e}")
            return []


def get_doctors_for_course_and_type(course, type_):
    """
    ترجع قائمة الأسماء الفريدة للدكاترة المتاحين لمقرر ونوع محتوى معين.
    """
    with LOCK:
        try:
            sheet = client.open(GOOGLE_SHEET_NAME).worksheet("materials")
            rows = sheet.get_all_records()
            doctors = []
            for row in rows:
                if str(row.get("course")) == str(course) and str(row.get("type")) == str(type_):
                    d = row.get("doctor") or ""
                    if d and d not in doctors:
                        doctors.append(d)
            return doctors
        except Exception as e:
            print(f"❌ خطأ أثناء جلب أسماء الدكاترة: {e}")
            return []


# ======= الملفات المؤقتة (قبل تحديد المقرر) =======

def set_waiting_file(chat_id, flag):
    """
    إذا flag=False -> حذف حالة الانتظار لهذا chat_id من waiting_files.
    إذا flag=True -> لا نفعل شيئًا (سيتم إنشاء صف بعد رفع الملف)
    """
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        if not flag:
            # إعادة كتابة جميع الصفوف بدون هذا chat_id
            all_rows = sheet.get_all_records()
            new_rows = [r for r in all_rows if str(r.get("chat_id")) != str(chat_id)]
            sheet.clear()
            sheet.append_row(["chat_id", "file_id", "type", "doctor"])
            for row in new_rows:
                sheet.append_row([row.get("chat_id"), row.get("file_id"), row.get("type"), row.get("doctor") or ""])
        else:
            # اجعل صف مؤقت (إن لم يكن موجود) مع file_id فارغ مؤقتاً
            all_rows = sheet.get_all_records()
            for r in all_rows:
                if str(r.get("chat_id")) == str(chat_id):
                    return
            sheet.append_row([chat_id, "", "", ""])


def set_waiting_file_fileid(chat_id, file_id, type_, doctor=None):
    """
    حفظ/تحديث ملف مؤقت بعد رفعه: يضع file_id و type وربما doctor.
    """
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        all_rows = sheet.get_all_records()
        for i, row in enumerate(all_rows, start=2):
            if str(row.get("chat_id")) == str(chat_id):
                sheet.update(f"A{i}:D{i}", [[chat_id, file_id, type_, doctor or ""]])
                return
        # إذا لم يوجد، أضف صف جديد
        sheet.append_row([chat_id, file_id, type_, doctor or ""])


def set_waiting_file_doctor(chat_id, doctor):
    """
    تحديث حقل doctor في waiting_files لchat_id معين.
    """
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        all_rows = sheet.get_all_records()
        for i, row in enumerate(all_rows, start=2):
            if str(row.get("chat_id")) == str(chat_id):
                sheet.update(f"D{i}:D{i}", [[doctor]])
                return


def is_waiting_file(chat_id):
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        rows = sheet.get_all_records()
        return any(str(r.get("chat_id")) == str(chat_id) for r in rows)


def get_waiting_file(chat_id):
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        rows = sheet.get_all_records()
        for r in rows:
            if str(r.get("chat_id")) == str(chat_id):
                return {"file_id": r.get("file_id"), "type": r.get("type"), "doctor": r.get("doctor")}
        return None
