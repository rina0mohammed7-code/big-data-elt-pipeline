import csv
from datetime import datetime

def generate_delta(input_file, output_file):
    print("⏳ جاري توليد ملف التحديثات (Delta)...")
    
    # استخدام utf-8-sig لتجاهل الحرف المخفي (BOM) في بداية الملف
    with open(input_file, 'r', encoding='utf-8-sig') as infile:
        reader = list(csv.DictReader(infile))

    # أخذ 5 سجلات موجودة وتحديث حالتها
    updates = reader[:5]
    for row in updates:
        row['status'] = 'تم التوصيل'
        row['order_date'] = datetime.now().strftime('%d/%m/%Y')

    # إنشاء 5 سجلات جديدة كلياً
    inserts = []
    for i in range(5):
        new_row = reader[i].copy()
        new_row['order_id'] = f"NEW_DELTA_ORD_{i}"
        new_row['status'] = 'جديد'
        inserts.append(new_row)

    delta_data = updates + inserts

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=delta_data[0].keys())
        writer.writeheader()
        writer.writerows(delta_data)

    print(f"✅ تم إنشاء ملف الـ Delta بنجاح: {output_file} (10 سجلات)")

if __name__ == '__main__':
    generate_delta('data/sample_orders.csv', 'data/delta_orders.csv')