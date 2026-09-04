# 🚀 خط بيانات هجين لمعالجة بيانات الطلبات (Hybrid ELT Data Pipeline)

**مقدم للمناقشة والتقييم الأكاديمي - مقرر البيانات الضخمة (العملي)**
* **فريق التطوير:** رينا الجماعي، شهد الشاوش
* **المسار المتقدم المختار:** المسار B (التحميل التزايدي والموثوقية المتقدمة - Incremental Loading & Idempotency)

---

## 📌 1. نظرة عامة على المعمارية
تم تصميم وبناء خط بيانات (Data Pipeline) متكامل يعتمد على معمارية (ELT) لمعالجة وتحليل مجموعة بيانات ضخمة (12.6 جيجابايت، 30 مليون سجل). 
يقوم النظام بالآتي:
1. **اكتشاف ذكي (File Router):** يحدد محرك المعالجة المناسب بناءً على حجم الملف (Python Batch للصغير، و PySpark للكبير).
2. **تحميل خام (Raw Load):** تحميل السجلات بالكامل دون إسقاط إلى `orders_raw` للحفاظ على النسخة الأصلية.
3. **تنظيف وتصنيف (Transform & Classify):** تمرير البيانات على فلاتر الجودة وتصنيفها إلى `Validated` أو `Quarantined`.
4. **إدراج آمن (Idempotent Upsert):** حفظ البيانات السليمة في قاعدة البيانات دون تكرار.

---

## ⚙️ 2. إعداد بيئة العمل (Setup & Prerequisites)
يجب توفر بيئة العمل التالية لتشغيل المشروع:
* **Python 3.10+**
* **Apache Spark** مثبت ومربوط بمتغيرات البيئة (`SPARK_HOME`) مع **Java 11**.
* **MongoDB Community Server** يعمل على المنفذ الافتراضي `27017`.

**خطوات التثبيت:**
```powershell
# 1. تفعيل البيئة الوهمية
python -m venv venv_stable
.\venv_stable\Scripts\activate

# 2. تثبيت المكتبات المطلوبة
pip install pymongo pyspark

🚀 3. أوامر التشغيل (Execution Commands)
المشروع مصمم ليعمل من نقطة إدخال واحدة (main.py) كما هو مطلوب.

أ. استخراج عينة صغيرة للاختبار:

PowerShell
python src\create_small_sample.py --input "C:\path\to\orders_huge.csv" --rows 100000
ب. التشغيل التلقائي (File Router):

PowerShell
# سيختار Python Batch تلقائياً
python main.py --file "data\sample_orders.csv"

# سيختار PySpark تلقائياً
python main.py --file "C:\path\to\orders_huge.csv"
ج. مسار التميز (B) - التحميل التزايدي (Incremental Load):

PowerShell
# 1. توليد ملف تحديثات (Delta)
python src\generate_delta.py

# 2. التشغيل الأول (إدراج وتحديث)
python src\incremental_loader.py --delta_file data\delta_orders.csv

# 3. إثبات عدم التكرار (Idempotency - Unchanged)
python src\incremental_loader.py --delta_file data\delta_orders.csv
🧹 4. قواعد التنظيف وأثر التصحيح (Quality Rules & Audit Trail)
تم تنفيذ 8 قواعد جودة آلية للحفاظ على سلامة البيانات:

الأرقام العربية: تحويل الأرقام (مثل ٥٠٠٠) إلى أرقام لاتينية (5000).

فواصل الآلاف: إزالة الفواصل من المبالغ المالية لتسهيل الحسابات.

توحيد العملة: توحيد أي عملات غير قياسية إلى YER.

النصوص إلى أرقام: تحويل السعر المكتوب بالكلمات (مثل "خمسة آلاف") إلى قيم رقمية.

تنظيف الهاتف: إزالة المسافات ورمز الدولة +967 لتوحيد تنسيق أرقام الهواتف.

إصلاح البريد الإلكتروني: إزالة الرموز المكررة الخاطئة مثل @@ و ...

صيغة التاريخ: توحيد التواريخ إلى الصيغة القياسية DD/MM/YYYY.

المسافات والمرادفات: عمل Trim للنصوص وتوحيد حالات الطلب (مثل "مدفوع بالكامل" إلى "مدفوع").

ملاحظة: كل تعديل يتم حفظه في مصفوفة corrections داخل السجل لتتبع التغييرات (Audit Trail).

🛡️ 5. العزل المنطقي (Quarantine Strategy)
السجلات التي لا يمكن إنقاذها يتم عزلها برمز خطأ واضح (error_code):

MISSING_ORDER_ID: لغياب مفتاح العمل الأساسي.

CORRUPTED_ITEMS_JSON: للبيانات التالفة هيكلياً والتي فشل مترجم بايثون في إنقاذها.

INVALID_IMPOSSIBLE_DATE: للتواريخ غير المنطقية.

🧠 6. القرارات الهندسية (Engineering Decisions)
فصل الاستخراج عن التنظيف (Decoupling): واجهنا مشكلة في تمزق نصوص JSON عبر PySpark، فقررنا تحميل البيانات خام (Raw) كأولوية قصوى، ثم تكليف كود Python لاحقاً بمهام التنظيف الدقيقة.

الأداء والذاكرة: للتعامل مع جهاز بذاكرة 8GB، استبدلنا أوامر القراءة الفردية (find_one) بعمليات الإدراج المجمعة الضخمة (BulkWrite) مع بناء فهارس (Indexes) على order_id، مما رفع سرعة المعالجة إلى أكثر من 3300 سجل/ثانية.

الـ Idempotency: اعتمدنا order_id كمفتاح عمل ثابت (Stable Business Key) مع استخدام Upsert، مما يضمن أن إعادة المعالجة لا تُنشئ بيانات مكررة إطلاقاً.

📊 7. التقارير والمقاييس (Metrics)
ينشئ النظام تقريراً آلياً في reports/results.json بعد كل تشغيل، يتضمن:

run_id ومعلومات الملف والمحرك المستخدم.

throughput (عدد السجلات في الثانية).

عدادات مفصلة: valid_count, corrected_count, quarantine_count.

ه

```powershell
git rm -r --cached venv_stable
git add README.md
git commit -m "إصلاح التوثيق وإزالة البيئة الوهمية"
git push
