import csv
import time
import sys
import os
import argparse
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# ربط المسار للوصول إلى الإعدادات
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME

def load_raw_batch(file_path, run_id, batch_size=5000):
    """
    قراءة الملف بصيغة Streaming وتحميله على دفعات إلى orders_raw
    """
    print("=" * 60)
    print(f"🚀 بدء التحميل الدفعي (Batch Load) للملف: {file_path}")
    
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    raw_collection = db["orders_raw"]
    
    start_time = time.time()
    total_records = 0
    batch = []
    
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=1):
                # تغليف السجل بالبيانات الوصفية المطلوبة في طبقة Raw (المتطلب 6.5)
                record = {
                    "run_id": run_id,
                    "source_file": os.path.basename(file_path),
                    "source_row_number": row_num,
                    "ingested_at": datetime.utcnow(),
                    "engine_used": "python_batch",
                    "raw_record": row  # السجل الأصلي كاملاً بدون أي تغيير
                }
                batch.append(record)
                
                # إدخال الدفعة عند الوصول للحجم المحدد
                if len(batch) >= batch_size:
                    _insert_batch(raw_collection, batch, total_records)
                    total_records += len(batch)
                    batch = [] # تفريغ الدفعة للبدء من جديد
            
            # إدخال ما تبقى من السجلات في الدفعة الأخيرة
            if batch:
                _insert_batch(raw_collection, batch, total_records)
                total_records += len(batch)
                
        elapsed_time = time.time() - start_time
        throughput = total_records / elapsed_time if elapsed_time > 0 else 0
        
        print("-" * 60)
        print(f"✅ اكتمل التحميل الخام بنجاح!")
        print(f"📊 إجمالي السجلات : {total_records}")
        print(f"⏱️ الزمن المستغرق  : {elapsed_time:.2f} ثانية")
        print(f"⚡ معدل الإدخال   : {throughput:.2f} سجل/ثانية")
        print("=" * 60)
        
        return total_records, elapsed_time
        
    except Exception as e:
        print(f"❌ حدث خطأ فادح أثناء قراءة الملف: {e}")
        return 0, 0
    finally:
        client.close()

def _insert_batch(collection, batch, total_records_so_far):
    """دالة مساعدة لإدخال الدفعة ومعالجة أخطائها"""
    try:
        collection.insert_many(batch)
        print(f"✔️ تم تحميل الدفعة... (إجمالي ما تم تحميله حتى الآن: {total_records_so_far + len(batch)} سجل)")
    except BulkWriteError as bwe:
        print(f"⚠️ خطأ جزئي أثناء تحميل الدفعة: {bwe.details}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع في الدفعة: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="اختبار التحميل الدفعي للبيانات الخام")
    parser.add_argument("--input", required=True, help="مسار الملف")
    parser.add_argument("--run_id", default="test_run_001", help="معرف التشغيل")
    
    args = parser.parse_args()
    load_raw_batch(args.input, args.run_id)