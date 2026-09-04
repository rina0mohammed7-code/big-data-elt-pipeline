import os

# حد حجم الملف بالميجابايت لتحديد المحرك (كما هو مطلوب في التكليف)
# نستخدم 200 ميجابايت كحد أقصى للملفات الصغيرة لضمان عدم إرهاق الذاكرة (8GB RAM)
SMALL_FILE_THRESHOLD_MB = int(os.getenv("SMALL_FILE_THRESHOLD_MB", 200))

# إعدادات قاعدة البيانات (سنحتاجها في الخطوات القادمة)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "midterm_db"
# config/settings.py
SMALL_FILE_THRESHOLD_MB = 200  # الحد الفاصل لاختيار محرك المعالجة (بالميجابايت)