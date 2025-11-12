import os
import threading
import json
import gspread
from google.oauth2.service_account import Credentials

# 🔒 قفل لتفادي التداخل بين الطلبات
LOCK = threading.Lock()

# ===== إعداد Google Sheets =====

# اسم ورقة العمل (يمكن تغييره من المتغير البيئي أو مباشرة هنا)
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "MedBot Files")

# الصلاحيات المطلوبة (تُضيف access إلى Sheets + Drive)
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
