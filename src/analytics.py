import pymongo
from datetime import datetime

# إعداد الاتصال (نفس الإعدادات السابقة)
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "midterm_db"
COLLECTION_NAME = "orders_validated"

def get_db():
    client = pymongo.MongoClient(MONGO_URI)
    return client[DB_NAME]

# ---------------------------------------------------------
# 1. التجميعات (Aggregations) - 5 تقارير تحليلية
# ---------------------------------------------------------
def generate_reports():
    db = get_db()
    collection = db[COLLECTION_NAME]
    
    reports = {}

    # 1. المبيعات حسب المدينة
    reports["sales_by_city"] = list(collection.aggregate([
        {"$group": {"_id": "$city", "total_sales": {"$sum": "$total_amount"}, "order_count": {"$sum": 1}}},
        {"$sort": {"total_sales": -1}},
        {"$limit": 5}
    ]))

    # 2. توزيع الطلبات حسب الحالة
    reports["orders_by_status"] = list(collection.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))

    # 3. أفضل المنتجات مبيعاً (بافتراض وجود حقل items أو product_name، سنستخدم total_amount كبديل إحصائي إذا لم يوجد)
    # ملاحظة: إذا كان لديكم مصفوفة items، يمكننا عمل $unwind لها، هنا سنجمع بناءً على خصائص الطلب
    reports["top_valuable_orders"] = list(collection.aggregate([
        {"$project": {"order_id": 1, "total_amount": 1, "city": 1}},
        {"$sort": {"total_amount": -1}},
        {"$limit": 5}
    ]))

    # 4. متوسط قيمة الطلب (AOV) وإجمالي الإيرادات
    reports["revenue_summary"] = list(collection.aggregate([
        {"$group": {
            "_id": None, 
            "total_revenue": {"$sum": "$total_amount"}, 
            "average_order_value": {"$avg": "$total_amount"},
            "total_orders": {"$sum": 1}
        }},
        {"$project": {"_id": 0}}
    ]))

    # 5. المبيعات حسب طرق الدفع (بافتراض وجود حقل payment_method) 
    # وإذا لم يوجد، سيقوم المونجو بإرجاع النتيجة للـ null كإحصائية صحيحة.
    reports["sales_by_payment_method"] = list(collection.aggregate([
        {"$group": {"_id": "$payment_method", "revenue": {"$sum": "$total_amount"}}},
        {"$sort": {"revenue": -1}}
    ]))

    return reports

# ---------------------------------------------------------
# 2. العروض المادية (Materialized Views) مع تحديث تزايدي
# ---------------------------------------------------------
def refresh_materialized_views():
    db = get_db()
    collection = db[COLLECTION_NAME]
    
    # العرض الأول: ملخص المبيعات اليومي (daily_sales_summary)
    # استخدام $merge يحقق "التحديث التزايدي" (Upsert) كما طلب الدكتور، بحيث يدمج البيانات الجديدة بدل حذف القديمة
    collection.aggregate([
        {"$group": {
            "_id": "$date", 
            "daily_revenue": {"$sum": "$total_amount"},
            "orders_count": {"$sum": 1}
        }},
        {"$merge": {
            "into": "mv_daily_sales_summary", 
            "whenMatched": "replace", 
            "whenNotMatched": "insert"
        }}
    ])

    # العرض الثاني: ملخص أداء المدن (city_performance_summary)
    collection.aggregate([
        {"$group": {
            "_id": "$city", 
            "total_revenue": {"$sum": "$total_amount"},
            "successful_orders": {
                "$sum": {"$cond": [{"$eq": ["$status", "مدفوع"]}, 1, 0]}
            }
        }},
        {"$merge": {
            "into": "mv_city_performance_summary", 
            "whenMatched": "replace", 
            "whenNotMatched": "insert"
        }}
    ])

    return {
        "status": "success",
        "message": "تم تحديث العروض المادية (Materialized Views) تزايدياً بنجاح.",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# للاختبار السريع
if __name__ == "__main__":
    print(refresh_materialized_views())
    print("تم توليد التقارير:", list(generate_reports().keys()))