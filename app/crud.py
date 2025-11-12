import os
import threading
import json
import gspread
from google.oauth2.service_account import Credentials

# 🔒 قفل لتفادي التداخل بين الطلبات
LOCK = threading.Lock()

# ===== إعداد Google Sheets =====

# اسم ورقة العمل
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "MedBot Files")

# الصلاحيات المطلوبة
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# تحميل بيانات الحساب الخدمي من متغير البيئة
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ متغير البيئة GOOGLE_SERVICE_ACCOUNT_JSON غير موجود!")

creds_info = json.loads(SERVICE_ACCOUNT_JSON)
credentials = Credentials.from_service_account_info(creds_info, scopes=SCOPES)

# إنشاء عميل Google Sheets
client = gspread.authorize(credentials)

# ===== تهيئة الورقة =====
def init_db():
    """تهيئة ورقة Google Sheet (إنشاءها أو فتحها)"""
    with LOCK:
        try:
            try:
                spreadsheet = client.open(GOOGLE_SHEET_NAME)
            except gspread.SpreadsheetNotFound:
                spreadsheet = client.create(GOOGLE_SHEET_NAME)

            # إنشاء ورقة materials إن لم تكن موجودة
            sheet_titles = [s.title for s in spreadsheet.worksheets()]
            if "materials" not in sheet_titles:
                spreadsheet.add_worksheet(title="materials", rows=1000, cols=4)
                sheet = spreadsheet.worksheet("materials")
                sheet.append_row(["course", "type", "file_id"])
            else:
                sheet = spreadsheet.worksheet("materials")

            # إنشاء ورقة waiting_files إن لم تكن موجودة
            if "waiting_files" not in sheet_titles:
                spreadsheet.add_worksheet(title="waiting_files", rows=500, cols=3)
                sheet2 = spreadsheet.worksheet("waiting_files")
                sheet2.append_row(["chat_id", "file_id", "type"])

            print("✅ Google Sheet جاهز للاستخدام")

        except Exception as e:
            print(f"❌ خطأ أثناء التهيئة: {e}")

# ======= عمليات المواد الدائمة =======

def add_material(course, type_, file_id):
    """إضافة أو تحديث مادة في Google Sheet"""
    with LOCK:
        try:
            sheet = client.open(GOOGLE_SHEET_NAME).worksheet("materials")
            rows = sheet.get_all_records()

            # تحقق إذا كان موجود نفس course + type مسبقًا
            for i, row in enumerate(rows, start=2):  # الصف 1 للعناوين
                if row["course"] == course and row["type"] == type_:
                    sheet.update_cell(i, 3, file_id)  # تحديث file_id فقط
                    return

            # إذا لم يوجد، أضف صف جديد
            sheet.append_row([course, type_, file_id])
        except Exception as e:
            print(f"❌ خطأ أثناء إضافة المادة: {e}")

def get_material(course, type_):
    """استرجاع ملف من Google Sheet"""
    with LOCK:
        try:
            sheet = client.open(GOOGLE_SHEET_NAME).worksheet("materials")
            rows = sheet.get_all_records()
            for row in rows:
                if row["course"] == course and row["type"] == type_:
                    return {"course": row["course"], "type": row["type"], "file_id": row["file_id"]}
        except Exception as e:
            print(f"❌ خطأ أثناء البحث عن المادة: {e}")
        return None

# ======= الملفات المؤقتة (قبل تحديد المقرر) =======

def set_waiting_file(chat_id, flag):
    """تعيين حالة انتظار رفع الملف"""
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        if not flag:
            all_rows = sheet.get_all_records()
            new_rows = [r for r in all_rows if str(r["chat_id"]) != str(chat_id)]
            # حذف الكل وإعادة كتابة الباقي
            sheet.clear()
            sheet.append_row(["chat_id", "file_id", "type"])
            for row in new_rows:
                sheet.append_row([row["chat_id"], row["file_id"], row["type"]])
        # لو flag=True → لا حاجة لفعل شيء

def set_waiting_file_fileid(chat_id, file_id, type_):
    """حفظ الملف المرفوع مؤقتًا"""
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        all_rows = sheet.get_all_records()

        for i, row in enumerate(all_rows, start=2):
            if str(row["chat_id"]) == str(chat_id):
                sheet.update(f"A{i}:C{i}", [[chat_id, file_id, type_]])
                return

        # إذا لم يوجد، أضف صف جديد
        sheet.append_row([chat_id, file_id, type_])

def is_waiting_file(chat_id):
    """هل المستخدم في وضع انتظار ملف؟"""
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        rows = sheet.get_all_records()
        return any(str(r["chat_id"]) == str(chat_id) for r in rows)

def get_waiting_file(chat_id):
    """استرجاع الملف المؤقت"""
    with LOCK:
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet("waiting_files")
        rows = sheet.get_all_records()
        for r in rows:
            if str(r["chat_id"]) == str(chat_id):
                return {"file_id": r["file_id"], "type": r["type"]}
        return None
