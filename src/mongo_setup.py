import sys
import os
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

# ربط المسار للوصول إلى مجلد الإعدادات
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME

def setup_database():
    print("=" * 60)
    print("⏳ جاري الاتصال بقاعدة بيانات MongoDB...")
    
    client = None # تهيئة المتغير لضمان إغلاقه بأمان لاحقاً
    
    try:
        # الاتصال بقاعدة البيانات مع مهلة زمنية قصيرة لاكتشاف الأخطاء بسرعة
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping') # فحص الاتصال الفعلي
        print("✅ تم الاتصال بقاعدة البيانات بنجاح.")
        
        db = client[DATABASE_NAME]
        
        # 1. إنشاء المجموعات (Collections) المطلوبة في التكليف
        required_collections = ["orders_raw", "orders_validated", "orders_quarantine"]
        existing_collections = db.list_collection_names()
        
        for coll in required_collections:
            if coll not in existing_collections:
                db.create_collection(coll)
                print(f"📁 تم إنشاء المجموعة: {coll}")
            else:
                print(f"✔️ المجموعة {coll} موجودة مسبقاً.")
                
        # 2. إنشاء الفهارس (Indexes)
        print("⏳ جاري إعداد الفهارس (Indexes) لضمان الموثوقية...")
        
        # الأهم: متطلب 6.10 لضمان Idempotency ومنع تكرار Business Records
        db.orders_validated.create_index([("order_id", ASCENDING)], unique=True)
        print("✅ تم إنشاء/التحقق من Unique Index على 'order_id' في orders_validated.")
        
        # فهارس إضافية لتسريع الاستعلام عن مسار كل تشغيل
        db.orders_raw.create_index([("run_id", ASCENDING)])
        db.orders_quarantine.create_index([("run_id", ASCENDING)])
        db.orders_validated.create_index([("run_id", ASCENDING)])
        
        print("=" * 60)
        print("🎉 اكتمل إعداد قاعدة البيانات ومجموعاتها بنجاح وهي جاهزة لاستقبال البيانات.")
        print("=" * 60)
        
    except ConnectionFailure:
        print("❌ خطأ: لم نتمكن من الاتصال بـ MongoDB. هل البرنامج يعمل (Running) في جهازك؟")
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع: {e}")
    finally:
        # المتطلب 9: الإغلاق السليم والآمن لقاعدة البيانات
        if client is not None:
            client.close()
            print("🔒 تم إغلاق الاتصال بقاعدة البيانات بأمان.")

if __name__ == "__main__":
    setup_database()