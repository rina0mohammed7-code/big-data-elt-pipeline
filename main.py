import os
import argparse
import time
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from config.settings import SMALL_FILE_THRESHOLD_MB
from elt_pipeline import run_elt_pipeline
from batch_loader import load_raw_batch

def file_router(file_path):
    if not os.path.exists(file_path):
        print(f"❌ الملف غير موجود: {file_path}")
        return

    # حساب حجم الملف بالميجابايت
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    run_id = f"run_{int(time.time())}"
    file_name = os.path.basename(file_path)

    print("=" * 60)
    print(f"📁 مسار الملف: {file_path}")
    print(f"📊 حجم الملف: {file_size_mb:.2f} MB")
    print(f"🔑 معرف التشغيل (Run ID): {run_id}")
    
    # اختيار المحرك (المتطلب 6.2)
    if file_size_mb <= SMALL_FILE_THRESHOLD_MB:
        engine = "python_batch"
        print(f"⚙️ المحرك المختار: {engine}")
        print("📌 السبب: حجم الملف أقل من أو يساوي الحد الفاصل (200MB).")
        print("=" * 60)
        
        # تنفيذ التحميل الدفعي ثم المعالجة
        load_raw_batch(file_path, run_id)
        run_elt_pipeline(run_id, file_name, file_size_mb, engine)
        
    else:
        engine = "pyspark"
        print(f"⚙️ المحرك المختار: {engine}")
        print("📌 السبب: حجم الملف يتجاوز الحد الفاصل، يتطلب معالجة متوازية.")
        print("=" * 60)
        
        # 1. استدعاء محرك Spark لرفع البيانات
        print("⏳ جاري تحويل المهمة إلى Apache Spark...")
        from spark_loader import run_spark_pipeline
        run_spark_pipeline(file_path, run_id)
        
        # 2. الإضافة الجوهرية: تشغيل ELT تلقائياً بعد انتهاء Spark
        print("⏳ جاري بدء مرحلة تنظيف البيانات (ELT Pipeline)...")
        run_elt_pipeline(run_id, file_name, file_size_mb, engine)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="نقطة التشغيل الرئيسية لخط البيانات")
    parser.add_argument("--file", required=True, help="مسار ملف البيانات للمعالجة")
    
    args = parser.parse_args()
    file_router(args.file)