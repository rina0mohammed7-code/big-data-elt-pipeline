import csv
import os
from datetime import datetime

def create_delta_file(input_path, output_path):
    print("=" * 60)
    print("⏳ جاري إنشاء ملف Delta للاختبار...")
    
    if not os.path.exists(input_path):
        print(f"❌ الملف {input_path} غير موجود.")
        return

    try:
        delta_records = []
        
        with open(input_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            headers = reader.fieldnames
            
            # استخراج أول 5 سجلات وتعديلها (لتمثيل Updates)
            for i, row in enumerate(reader):
                if i >= 5: break
                row['status'] = 'تم التوصيل' # تغيير الحالة
                row['record_version'] = '2' # إصدار أحدث
                delta_records.append(row)
                
        # إضافة 5 سجلات جديدة كلياً (لتمثيل Inserts)
        for i in range(1, 6):
            new_row = {h: '' for h in headers}
            new_row['\ufefforder_id'] = f"DELTA-900{i}" # معالجة الـ BOM
            new_row['order_date'] = '15-02-2025'
            new_row['customer_id'] = f"CUST-D{i}"
            new_row['total_amount'] = '8500'
            new_row['items_json'] = '[{"item": "Laptop"}]'
            new_row['status'] = 'طلب جديد'
            new_row['record_version'] = '1' # إصدار أول
            delta_records.append(new_row)

        # حفظ ملف الـ Delta
        headers.append('record_version')
        with open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(delta_records)
            
        print(f"✅ تم إنشاء ملف Delta بنجاح في: {output_path}")
        print(f"📊 يحتوي على 5 سجلات معدلة (Updates) و 5 سجلات جديدة (Inserts).")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    create_delta_file("data/sample_orders.csv", "data/delta_orders.csv")