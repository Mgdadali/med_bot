# app/crud.py
import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")
LOCK = threading.Lock()  # لضمان التزامن عند الوصول للقاعدة

def init_db():
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # جدول المواد الدائم
        c.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                type TEXT NOT NULL,
                file_id TEXT NOT NULL UNIQUE
            )
        ''')
        # جدول الملفات المرفوعة مؤقتًا قبل تحديد المقرر
        c.execute('''
            CREATE TABLE IF NOT EXISTS waiting_files (
                chat_id INTEGER PRIMARY KEY,
                file_id TEXT NOT NULL,
                type TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

# ========= مواد دائمة =========
def add_material(course, type_, file_id):
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO materials (course, type, file_id) VALUES (?, ?, ?)",
            (course, type_, file_id)
        )
        conn.commit()
        conn.close()

def get_material(course, type_):
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT course, type, file_id FROM materials WHERE course=? AND type=?",
            (course, type_)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return {"course": row[0], "type": row[1], "file_id": row[2]}
        return None

# ========= ملفات مؤقتة قبل تحديد المقرر =========
def set_waiting_file(chat_id, flag):
    """حفظ حالة انتظار رفع الملف"""
    if not flag:
        # إزالة الملف المؤقت عند الانتهاء
        with LOCK:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM waiting_files WHERE chat_id=?", (chat_id,))
            conn.commit()
            conn.close()
    else:
        # لا نفعل شيئًا هنا، سيتم إضافة file_id لاحقًا
        pass

def set_waiting_file_fileid(chat_id, file_id, type_):
    """حفظ الملف المرفوع مؤقتًا"""
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO waiting_files (chat_id, file_id, type) VALUES (?, ?, ?)",
            (chat_id, file_id, type_)
        )
        conn.commit()
        conn.close()

def is_waiting_file(chat_id):
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT file_id FROM waiting_files WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        conn.close()
        return row is not None

def get_waiting_file(chat_id):
    """استرجاع الملف المرفوع مؤقتًا"""
    with LOCK:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT file_id, type FROM waiting_files WHERE chat_id=?", (chat_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"file_id": row[0], "type": row[1]}
        return None
