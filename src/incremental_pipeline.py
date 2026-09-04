import sys
import os
import csv
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME
from quality_rules import apply_quality_rules

def run_incremental_load(delta_file_path, run_id):
    print("=" * 60)
    print(f"🚀 بدء التحميل التزايدي (Incremental Load) - المسار المتقدم B")
    print("=" * 60)

    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    raw_coll = db["orders_raw"]
    validated_coll = db["orders_validated"]
    
    # 1. تحميل بيانات Delta إلى طبقة Raw (ELT Pattern)
    raw_batch = []
    try:
        with open(delta_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_batch.append({
                    "run_id": run_id,
                    "source_file": os.path.basename(delta_file_path),
                    "ingested_at": datetime.now(timezone.utc),
                    "raw_record": row
                })
        if raw_batch:
            raw_coll.insert_many(raw_batch)
            print(f"✅ تم تحميل {len(raw_batch)} سجل من ملف Delta إلى orders_raw")
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف Delta: {e}")
        return

    # 2. تطبيق قواعد الجودة والتحكم بالإصدارات (Version Handling)
    metrics = {"inserted": 0, "updated": 0, "ignored_older_version": 0}
    ops = []
    
    for doc in raw_batch:
        raw_data = doc["raw_record"]
        # معالجة المعرفات
        order_id = raw_data.get("order_id", raw_data.get("\ufefforder_id", "")).strip()
        
        # استخراج رقم الإصدار من ملف الدلتا (افتراضي 1 إذا لم يوجد)
        incoming_version = int(raw_data.get("record_version", 1))
        
        cleaned_data, status, corrections = apply_quality_rules(raw_data)
        cleaned_data["record_version"] = incoming_version # حفظ رقم الإصدار مع البيانات المنظفة
        
        final_doc = {
            "order_id": order_id,
            "run_id": run_id,
            "processed_data": cleaned_data,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # الذكاء الأساسي للمسار B: فحص تعارض التحديثات
        existing = validated_coll.find_one({"order_id": order_id})
        
        if not existing:
            # سجل جديد تماماً
            metrics["inserted"] += 1
            ops.append(UpdateOne({"order_id": order_id}, {"$set": final_doc}, upsert=True))
        else:
            # سجل موجود، يجب مقارنة الإصدارات لمنع التخريب
            existing_version = int(existing.get("processed_data", {}).get("record_version", 0))
            
            if incoming_version >= existing_version:
                metrics["updated"] += 1
                ops.append(UpdateOne({"order_id": order_id}, {"$set": final_doc}, upsert=True))
            else:
                # رفض التحديث لأن النسخة القادمة أقدم من الموجودة في قاعدة البيانات
                metrics["ignored_older_version"] += 1 

    # تنفيذ التحديثات المعتمدة فقط
    if ops:
        validated_coll.bulk_write(ops)

    print("-" * 60)
    print("🎉 اكتملت المعالجة الذكية للبيانات التزايدية (Version Handling)!")
    print(f"📥 سجلات جديدة (Inserted): {metrics['inserted']} (تثبت إدخال الطلبات الجديدة بسلاسة)")
    print(f"🔄 سجلات تم تحديثها (Updated): {metrics['updated']} (تثبت قبول النسخة الأحدث)")
    print(f"🛡️ سجلات تم تجاهلها (Ignored): {metrics['ignored_older_version']} (تثبت قوة حماية البيانات من النسخ القديمة!)")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    run_incremental_load("data/delta_orders.csv", "delta_run_001")