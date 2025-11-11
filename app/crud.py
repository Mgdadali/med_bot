# app/crud.py

# -------------------- قاعدة البيانات مبسطة --------------------
# تخزين المواد كقائمة من القواميس
materials = []  # كل عنصر: {"course": "تشريح", "type": "pdf", "file_id": "BQACAg..."}

# -------------------- دوال إدارة المواد --------------------
def add_material(course: str, ctype: str, file_id: str):
    """
    إضافة مادة جديدة أو تحديث الملف لنفس المادة والنوع.
    """
    # تحقق إذا المادة + النوع موجودة مسبقاً
    for mat in materials:
        if mat["course"] == course and mat["type"] == ctype:
            mat["file_id"] = file_id
            return
    # إذا غير موجود، أضف جديد
    materials.append({"course": course, "type": ctype, "file_id": file_id})

def get_material(course: str, ctype: str):
    """
    جلب المادة حسب الاسم والنوع.
    """
    for mat in materials:
        if mat["course"] == course and mat["type"] == ctype:
            return mat
    return None

def list_materials():
    """
    استعراض جميع المواد.
    """
    return materials

# -------------------- دعم انتظار الملف للأدمن --------------------
# key = chat_id, value = True/False
waiting_files = {}

def set_waiting_file(chat_id, value: bool):
    waiting_files[chat_id] = value

def is_waiting_file(chat_id):
    return waiting_files.get(chat_id, False)
