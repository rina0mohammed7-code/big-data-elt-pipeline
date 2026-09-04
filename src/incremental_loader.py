import sys
import os
import csv
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME
from quality_rules import apply_quality_rules

def run_incremental_load(delta_file):
    print("=" * 60)
    print(f"🚀 بدء التحميل التزايدي (Incremental Load) للملف: {delta_file}")
    
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    validated_coll = db["orders_validated"]
    
    metrics = {"inserted": 0, "updated": 0, "unchanged": 0}
    ops = []
    
    with open(delta_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned_data, status, _ = apply_quality_rules(row)
            order_id = row.get("order_id") or row.get("\ufefforder_id")
            
            doc = {
                "order_id": order_id,
                "processed_data": cleaned_data,
                "quality_status": status,
                "last_updated": datetime.now(timezone.utc)
            }
            
            existing = validated_coll.find_one({"order_id": order_id})
            
            if not existing:
                metrics["inserted"] += 1
                ops.append(UpdateOne({"order_id": order_id}, {"$set": doc}, upsert=True))
            else:
                if existing.get("processed_data") != cleaned_data:
                    metrics["updated"] += 1
                    ops.append(UpdateOne({"order_id": order_id}, {"$set": doc}))
                else:
                    metrics["unchanged"] += 1

    if ops:
        validated_coll.bulk_write(ops, ordered=False)
        
    print("✅ اكتمل التحميل التزايدي بنجاح!")
    print(f"📥 سجلات جديدة (Inserted): {metrics['inserted']}")
    print(f"🔄 سجلات محدثة (Updated) : {metrics['updated']}")
    print(f"⏸️ سجلات لم تتغير (Unchanged): {metrics['unchanged']}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta_file", required=True)
    args = parser.parse_args()
    run_incremental_load(args.delta_file)