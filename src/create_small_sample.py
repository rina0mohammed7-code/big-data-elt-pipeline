import csv
import argparse
import os

def create_sample(input_path, output_path, rows):
    if not os.path.exists(input_path):
        print(f"❌ الملف الأصلي غير موجود: {input_path}")
        return

    try:
        with open(input_path, mode='r', encoding='utf-8') as infile, \
             open(output_path, mode='w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # كتابة الترويسة (Header)
            headers = next(reader)
            writer.writerow(headers)
            
            # استخراج العدد المطلوب من الصفوف
            count = 0
            for row in reader:
                if count >= rows:
                    break
                writer.writerow(row)
                count += 1
                
        print(f"✅ تم إنشاء العينة بنجاح: {output_path} ({count} صف)")
    except Exception as e:
        print(f"❌ خطأ أثناء إنشاء العينة: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="استخراج عينة صغيرة من الملف الضخم")
    parser.add_argument("--input", required=True, help="مسار الملف الأصلي")
    parser.add_argument("--output", default="data/sample_orders.csv", help="مسار الحفظ")
    parser.add_argument("--rows", type=int, default=100000, help="عدد الصفوف")
    
    args = parser.parse_args()
    create_sample(args.input, args.output, args.rows)