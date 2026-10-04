import time
import schedule
from datetime import datetime
import pymongo
import sys
import os

# ضمان القدرة على استيراد الدوال من الملفات الأخرى
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from analytics import refresh_materialized_views, generate_reports

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "midterm_db"

def get_jobs_collection():
    client = pymongo.MongoClient(MONGO_URI)
    # جدول جديد مخصص لتسجيل حركة المهام (Logs)
    return client[DB_NAME]["scheduled_jobs_log"]

def log_job_execution(job_name, status, start_time, end_time, details=""):
    """تسجيل تفاصيل تنفيذ المهمة في قاعدة البيانات"""
    collection = get_jobs_collection()
    log_entry = {
        "job_name": job_name,
        "status": status,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": (end_time - start_time).total_seconds(),
        "details": details
    }
    collection.insert_one(log_entry)
    print(f"[{end_time.strftime('%H:%M:%S')}] تم تسجيل المهمة {job_name}: {status}")

# ---------------------------------------------------------
# 1. المهمة الأولى: تحديث العروض المادية (Materialized Views)
# ---------------------------------------------------------
def job_refresh_mvs():
    start_time = datetime.now()
    print(f"[{start_time.strftime('%H:%M:%S')}] بدء مهمة تحديث العروض المادية...")
    try:
        result = refresh_materialized_views()
        end_time = datetime.now()
        log_job_execution("Refresh_Materialized_Views", "Success", start_time, end_time, result)
        return {"status": "Success", "details": result}
    except Exception as e:
        end_time = datetime.now()
        log_job_execution("Refresh_Materialized_Views", "Failed", start_time, end_time, str(e))
        return {"status": "Failed", "error": str(e)}

# ---------------------------------------------------------
# 2. المهمة الثانية: إنشاء التقارير الدورية
# ---------------------------------------------------------
def job_generate_reports():
    start_time = datetime.now()
    print(f"[{start_time.strftime('%H:%M:%S')}] بدء مهمة توليد التقارير التجميعية...")
    try:
        reports = generate_reports()
        summary = f"تم توليد التقارير: {list(reports.keys())}"
        end_time = datetime.now()
        log_job_execution("Generate_Aggregations_Report", "Success", start_time, end_time, summary)
        return {"status": "Success", "details": summary}
    except Exception as e:
        end_time = datetime.now()
        log_job_execution("Generate_Aggregations_Report", "Failed", start_time, end_time, str(e))
        return {"status": "Failed", "error": str(e)}

# ---------------------------------------------------------
# إعداد الجدول الزمني
# ---------------------------------------------------------
# تعمل كل ساعة
schedule.every(1).hours.do(job_refresh_mvs)
# تعمل يومياً منتصف الليل
schedule.every().day.at("23:59").do(job_generate_reports)

def run_scheduler():
    print("بدأ تشغيل الجدولة التلقائية... (اضغط Ctrl+C للإيقاف)")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # تشغيل يدوي للاختبار أثناء المناقشة كما طلب الدكتور
    print("--- تشغيل اختباري يدوي للمهام ---")
    job_refresh_mvs()
    job_generate_reports()