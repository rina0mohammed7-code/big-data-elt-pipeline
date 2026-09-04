import os
import sys
import uuid

# السماح للسكربت بالوصول إلى مجلد config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import SMALL_FILE_THRESHOLD_MB

def get_file_size_mb(file_path):
    """حساب حجم الملف بالميجابايت"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"خطأ: الملف غير موجود في المسار: {file_path}")
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    return size_mb

def route_file(file_path):
    """تحديد المحرك المناسب بناءً على حجم الملف وإنشاء run_id"""
    size_mb = get_file_size_mb(file_path)
    run_id = str(uuid.uuid4()) # إنشاء معرف تشغيل فريد (المرحلة 1 في التكليف)
    
    if size_mb <= SMALL_FILE_THRESHOLD_MB:
        engine = "python_batch"
        reason = f"حجم الملف ({size_mb:.2f} MB) أصغر من أو يساوي الحد الفاصل ({SMALL_FILE_THRESHOLD_MB} MB)."
    else:
        engine = "pyspark"
        reason = f"حجم الملف ({size_mb:.2f} MB) كبير جداً ويتطلب معالجة متوازية."
        
    print("=" * 60)
    print("🚀 بدء توجيه الملف (File Router)")
    print("=" * 60)
    print(f"📁 مسار الملف    : {file_path}")
    print(f"📊 حجم الملف    : {size_mb:.2f} MB")
    print(f"🔑 معرف التشغيل : {run_id}")
    print(f"⚙️ المحرك المختار: {engine}")
    print(f"📝 سبب الاختيار  : {reason}")
    print("=" * 60)
    
    return engine, run_id, size_mb

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="اختبار الموجه التلقائي (File Router)")
    parser.add_argument("--input", required=True, help="مسار الملف لاختباره")
    
    args = parser.parse_args()
    route_file(args.input)