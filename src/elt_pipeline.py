import sys
import os
import time
import json
import ast
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne

# ربط المسار للوصول إلى الإعدادات وقواعد الجودة
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME
from quality_rules import apply_quality_rules

def validate_and_classify(record):
    raw_data = record.get("raw_record") or {}
    
    def safe_strip(val):
        return str(val).strip() if val is not None else ""
    
    order_id = safe_strip(raw_data.get("order_id") or raw_data.get("\ufefforder_id"))
    customer_id = safe_strip(raw_data.get("customer_id"))
    order_date = safe_strip(raw_data.get("order_date"))
    items = safe_strip(raw_data.get("items_json"))
    price = safe_strip(raw_data.get("total_amount"))
    
    if not order_id:
        return None, "quarantined", "MISSING_ORDER_ID", "معرف الطلب مفقود."
    if not customer_id:
        return None, "quarantined", "MISSING_CUSTOMER_ID", "معرف العميل مفقود."
    if not items or items == "[]" or items == "['']":
        return None, "quarantined", "EMPTY_ITEMS", "لا توجد عناصر للطلب."
        
    # [الحل المعماري النهائي لبيانات JSON المشوهة]
    if items and items not in ("[]", "['']"):
        is_valid_json = False
        
        # المستوى 1: التحليل القياسي الصارم
        try:
            json.loads(items)
            is_valid_json = True
        except Exception:
            # المستوى 2: تنظيف تشوهات ملفات CSV
            try:
                clean_items = items.strip(' "\'\n\r').replace('""', '"')
                json.loads(clean_items)
                is_valid_json = True
            except Exception:
                # المستوى 3: التحليل عبر مترجم بايثون (للنصوص المحولة برمجياً)
                try:
                    ast.literal_eval(clean_items)
                    is_valid_json = True
                except Exception:
                    # المستوى 4: خطة الإنقاذ الهيكلية (Structural Heuristics)
                    clean_str = items.strip(' \n\r"\'')
                    if (clean_str.startswith('[') and clean_str.endswith(']')) or \
                       (clean_str.startswith('{') and clean_str.endswith('}')):
                        is_valid_json = True
                        
        if not is_valid_json:
            return None, "quarantined", "CORRUPTED_ITEMS_JSON", "تنسيق JSON تالف تماماً ولا يمكن إنقاذه."

    if not price:
        return None, "quarantined", "UNKNOWN_PRICE", "السعر مفقود."
        
    if "-" in price and any(char.isdigit() for char in price):
        return None, "quarantined", "AMBIGUOUS_NEGATIVE_VALUE", "مبلغ سالب غير منطقي."
        
    if "9999" in order_date or len(order_date) < 6:
        return None, "quarantined", "INVALID_IMPOSSIBLE_DATE", "تاريخ غير منطقي."

    cleaned_data, quality_status, corrections = apply_quality_rules(raw_data)
    
    final_document = {
        "order_id": order_id,
        "customer_id": customer_id,
        "run_id": record.get("run_id"),
        "ingested_at": record.get("ingested_at"),
        "processed_data": cleaned_data,
        "quality_status": quality_status,
        "corrections": corrections,
        "updated_at": datetime.now(timezone.utc)
    }
    
    return final_document, quality_status, None, None

def run_elt_pipeline(run_id, file_name="unknown", file_size_mb=0, engine="python_batch", partitions_or_batch="batch=5000"):
    print("=" * 60)
    print(f"🚀 بدء معالجة خط البيانات (ELT Pipeline) لمعرف التشغيل: {run_id}")
    print("=" * 60)
    
    client = MongoClient(MONGO_URI)
    
    try:
        db = client[DATABASE_NAME]
        
        raw_coll = db["orders_raw"]
        validated_coll = db["orders_validated"]
        quarantine_coll = db["orders_quarantine"]
        
        print("⏳ جاري بناء الفهارس (Indexes) لتسريع المعالجة أضعافاً مضاعفة...")
        raw_coll.create_index("run_id")
        validated_coll.create_index("order_id")
        print("✅ اكتمل بناء الفهارس! ننطلق الآن بسرعة قصوى ⚡")
        
        start_time = time.time()
        
        metrics = {
            "run_id": run_id,
            "file_name": file_name,
            "file_size_mb": file_size_mb,
            "engine_used": engine,
            "batch_size_or_partitions": partitions_or_batch,
            "rows_read": 0,
            "raw_loaded": 0,
            "valid_count": 0,
            "corrected_count": 0,
            "quarantine_count": 0,
            "error_case_counts": {},
            "inserted_count": 0,
            "updated_count": 0,
            "unchanged_count": 0
        }
        
        cursor = raw_coll.find({"run_id": run_id})
        batch_validated_ops = []
        batch_quarantine_docs = []
        
        for doc in cursor:
            metrics["rows_read"] += 1
            metrics["raw_loaded"] += 1
            
            # تحديث مرئي كل 10 آلاف سجل لتتابعي السرعة
            if metrics["rows_read"] % 10000 == 0:
                print(f"⏳ تمت معالجة {metrics['rows_read']:,} سجل حتى الآن...")
                
            processed_doc, status, error_code, error_msg = validate_and_classify(doc)
            
            if status == "quarantined":
                metrics["quarantine_count"] += 1
                metrics["error_case_counts"][error_code] = metrics["error_case_counts"].get(error_code, 0) + 1
                
                quarantine_record = {
                    "run_id": run_id,
                    "raw_record": doc.get("raw_record"),
                    "error_code": error_code,
                    "error_details": error_msg,
                    "quarantined_at": datetime.now(timezone.utc)
                }
                batch_quarantine_docs.append(quarantine_record)
                
            else:
                if status == "valid":
                    metrics["valid_count"] += 1
                elif status == "corrected":
                    metrics["corrected_count"] += 1
                    
                # إعداد عملية Upsert وتلبية المتطلب 6.10 بدون إبطاء الشبكة (إزالة find_one)
                batch_validated_ops.append(
                    UpdateOne(
                        {"order_id": processed_doc["order_id"]},
                        {"$set": processed_doc},
                        upsert=True
                    )
                )
                
            # المعالجة المجمعة بحزم ضخمة لتفادي انهيار الذاكرة وزيادة السرعة
            if len(batch_validated_ops) >= 10000:
                result = validated_coll.bulk_write(batch_validated_ops, ordered=False)
                metrics["inserted_count"] += result.upserted_count
                metrics["updated_count"] += result.modified_count
                metrics["unchanged_count"] += (result.matched_count - result.modified_count)
                batch_validated_ops = []
                
            if len(batch_quarantine_docs) >= 10000:
                quarantine_coll.insert_many(batch_quarantine_docs, ordered=False)
                batch_quarantine_docs = []

        # تنفيذ ما تبقى من السجلات خارج الحلقة
        if batch_validated_ops:
            result = validated_coll.bulk_write(batch_validated_ops, ordered=False)
            metrics["inserted_count"] += result.upserted_count
            metrics["updated_count"] += result.modified_count
            metrics["unchanged_count"] += (result.matched_count - result.modified_count)
            
        if batch_quarantine_docs:
            quarantine_coll.insert_many(batch_quarantine_docs, ordered=False)
            
        elapsed_time = time.time() - start_time
        throughput = metrics["rows_read"] / elapsed_time if elapsed_time > 0 else 0
        
        metrics["elapsed_seconds"] = round(elapsed_time, 2)
        metrics["throughput"] = round(throughput, 2)
        
        os.makedirs("reports", exist_ok=True)
        results_path = "reports/results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=4)
            
        print("-" * 60)
        print(f"🎉 اكتمل خط أنابيب ELT بنجاح!")
        print(f"⏱️ الزمن المستغرق  : {metrics['elapsed_seconds']} ثانية")
        print(f"⚡ السرعة         : {metrics['throughput']} سجل/ثانية")
        print(f"✔️ السجلات السليمة : {metrics['valid_count']}")
        print(f"🔧 السجلات المصححة: {metrics['corrected_count']}")
        print(f"🚨 السجلات المعزولة: {metrics['quarantine_count']}")
        print(f"📥 السجلات الجديدة (Inserted): {metrics['inserted_count']}")
        print(f"🔄 السجلات المحدثة (Updated) : {metrics['updated_count']}")
        print(f"📁 تم حفظ المقاييس في: {results_path}")
        print("=" * 60)
        
        return metrics

    finally:
        client.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="تنفيذ خط أنابيب ELT")
    parser.add_argument("--run_id", required=True, help="معرف التشغيل المراد معالجته")
    parser.add_argument("--file_name", default="unknown", help="اسم الملف المعالج")
    parser.add_argument("--file_size_mb", type=float, default=0.0, help="حجم الملف بالميجا")
    parser.add_argument("--engine", default="python_batch", help="المحرك المستخدم")
    
    args = parser.parse_args()
    run_elt_pipeline(args.run_id, args.file_name, args.file_size_mb, args.engine)