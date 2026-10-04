import pymongo

# إعداد الاتصال بقاعدة البيانات
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "midterm_db" 
COLLECTION_NAME = "orders_validated"

def get_collection():
    client = pymongo.MongoClient(MONGO_URI)
    return client[DB_NAME][COLLECTION_NAME]

# ---------------------------------------------------------
# 1. الفهارس (Indexes) - إنشاء 3 فهارس منها واحد مركب
# ---------------------------------------------------------
def create_custom_indexes():
    collection = get_collection()
    
    # 1. فهرس عادي على المدينة لتسريع البحث الجغرافي (داخل الكائن المتداخل)
    collection.create_index([("processed_data.city", pymongo.ASCENDING)], name="idx_city")
    
    # 2. فهرس عادي على المبالغ لتسريع الفرز المالي
    collection.create_index([("processed_data.total_amount", pymongo.DESCENDING)], name="idx_total_amount")
    
    # 3. فهرس مركب على حالة الطلب والتاريخ 
    collection.create_index([("processed_data.status", pymongo.ASCENDING), ("processed_data.date", pymongo.DESCENDING)], name="idx_status_date_compound")
    
    return {"message": "تم إنشاء الفهارس الثلاثة (بما فيها الفهرس المركب) بنجاح."}

# ---------------------------------------------------------
# 2. الاستعلامات (Queries) - تنفيذ 5 استعلامات عملية
# ---------------------------------------------------------
def run_five_queries():
    collection = get_collection()
    
    return {
        # 1. البحث عن الطلبات السليمة باستخدام حقل الجودة الخارجي
        "query_1_valid_orders": list(collection.find({"quality_status": "valid"}, {"_id": 0}).limit(2)),
        
        # 2. البحث عن الطلبات المصححة
        "query_2_corrected_orders": list(collection.find({"quality_status": "corrected"}, {"_id": 0}).limit(2)),
        
        # 3. أحدث الطلبات التي تم تحديثها
        "query_3_recent_updates": list(collection.find({}, {"_id": 0}).sort("updated_at", -1).limit(2)),
        
        # 4. البحث داخل البيانات المتداخلة (الطلبات ذات القيمة العالية)
        "query_4_high_value": list(collection.find({"processed_data.total_amount": {"$gt": 1000}}, {"_id": 0}).limit(2)),
        
        # 5. التأكد من وجود بيانات الحالة للطلبات
        "query_5_nested_status": list(collection.find({"processed_data.status": {"$exists": True}}, {"_id": 0}).limit(2))
    }

# ---------------------------------------------------------
# 3. الـ Explain (قبل وبعد) مع التبرير والتأثير
# ---------------------------------------------------------
def explain_queries_comparison():
    collection = get_collection()
    results = {}
    
    # استخدام الحقول المتداخلة المطابقة للفهارس
    queries = {
        "q1_city": {"processed_data.city": "صنعاء"},
        "q2_amount": {"processed_data.total_amount": {"$gt": 15000}},
        "q3_compound": {"processed_data.status": "مدفوع"}
    }

    # -- المرحلة أ: حذف الفهارس (لمعرفة الأداء قبل الفهرسة) --
    for index_name in ["idx_city", "idx_total_amount", "idx_status_date_compound"]:
        try:
            collection.drop_index(index_name)
        except:
            pass

    results["before_indexes"] = {}
    for q_name, q_filter in queries.items():
        stats = collection.find(q_filter).explain()["executionStats"]
        results["before_indexes"][q_name] = {
            "executionTimeMillis": stats.get("executionTimeMillis"),
            "totalDocsExamined": stats.get("totalDocsExamined"),
            "stage": stats.get("executionStages", {}).get("stage") # عادة COLLSCAN
        }

    # -- المرحلة ب: إنشاء الفهارس مجدداً --
    create_custom_indexes()

    # -- المرحلة ج: قياس الأداء (بعد الفهرسة) --
    results["after_indexes"] = {}
    for q_name, q_filter in queries.items():
        cursor = collection.find(q_filter)
        if q_name == "q3_compound":
            cursor = cursor.sort("processed_data.date", -1) # تفعيل الفهرس المركب
            
        stats = cursor.explain()["executionStats"]
        results["after_indexes"][q_name] = {
            "executionTimeMillis": stats.get("executionTimeMillis"),
            "totalDocsExamined": stats.get("totalDocsExamined"),
            "stage": stats.get("executionStages", {}).get("stage") # عادة IXSCAN
        }

    # -- المرحلة د: التبرير والأثر --
    results["analysis_and_reasons"] = {
        "idx_city": "تم اختياره لأن البحث بالمدينة شائع، الأثر: تجنب المسح الشامل (COLLSCAN) للملايين من السجلات واستبداله بـ (IXSCAN).",
        "idx_total_amount": "تم اختياره لتسريع استخراج الطلبات ذات القيمة العالية (VIP)، الأثر: تقليل وقت الفرز (Sort) وعمليات الفلترة.",
        "idx_status_date_compound": "فهرس مركب تم اختياره لأن الإدارة غالباً تطلب (حالة الطلب) مرتبة تنازلياً حسب (التاريخ). الأثر: تحقيق التغطية الكاملة (Covered Query) لاستعلامين في نفس الوقت."
    }
    
    return results

# لاختبار الملف بشكل مستقل مؤقتاً
if __name__ == "__main__":
    print(create_custom_indexes())
    print("Queries Done: ", len(run_five_queries()))