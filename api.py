from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn

# استيراد الدوال التي أنشأناها في الخطوات السابقة من مجلد src
from src.db_operations import create_custom_indexes, run_five_queries, explain_queries_comparison
from src.analytics import generate_reports, refresh_materialized_views
from src.scheduler_jobs import job_refresh_mvs, job_generate_reports

# استيراد دالة الإدخال الأساسية من ملف main.py
from main import file_router

app = FastAPI(
    title="Hybrid ELT Pipeline API",
    description="واجهة موحدة لتشغيل واختبار وظائف المشروع النهائي لمقرر البيانات الضخمة.",
    version="1.0.0"
)

# 1. فحص حالة النظام
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running smoothly."}

# نموذج بيانات لاستقبال مسار الملف
class IngestRequest(BaseModel):
    file_path: str

# 2. تشغيل الـ Pipeline في الخلفية لتجنب تجميد الواجهة (يعتمد على نفس بوابة الإدخال)
@app.post("/ingest")
def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(file_router, request.file_path)
    return {"status": "Accepted", "message": f"تم بدء معالجة الملف '{request.file_path}' في الخلفية."}

# 3. الفهارس
@app.post("/indexes")
def create_indexes():
    return create_custom_indexes()

# 4. الاستعلامات (مع مسار إضافي للـ Explain كما طلب الدكتور)
@app.get("/queries")
def run_queries():
    return run_five_queries()

@app.get("/queries/explain")
def explain_queries():
    return explain_queries_comparison()

# 5. التجميعات (التقارير)
@app.get("/aggregations")
def get_aggregations():
    return generate_reports()

# 6. تحديث العروض المادية
@app.post("/refresh-mv")
def refresh_mv():
    return refresh_materialized_views()

# 7. المهام المجدولة (عرض وتشغيل)
@app.get("/jobs")
def list_jobs():
    return {
        "available_jobs": [
            {"name": "job_refresh_mvs", "description": "تحديث العروض المادية تزايدياً"},
            {"name": "job_generate_reports", "description": "توليد التقارير التجميعية"}
        ]
    }

@app.post("/jobs/{name}/run")
def run_job(name: str):
    if name == "job_refresh_mvs":
        return job_refresh_mvs()
    elif name == "job_generate_reports":
        return job_generate_reports()
    else:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة. يرجى التحقق من الاسم.")

if __name__ == "__main__":
    print("🚀 جاري تشغيل الخادم... افتح الرابط: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)