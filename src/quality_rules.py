import re

def clean_arabic_numbers(val):
    """القاعدة 1: تحويل الأرقام العربية إلى لاتينية"""
    if not isinstance(val, str): return val
    arabic_to_latin = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    new_val = val.translate(arabic_to_latin)
    return new_val if new_val != val else val

def clean_currency(val):
    """القاعدة 2: إزالة النصوص والعملات وتوحيدها"""
    if not isinstance(val, str): return val
    new_val = re.sub(r'(ريال|يمني|yer|YER|ryal|ر.ي)\s*', '', val, flags=re.IGNORECASE).strip()
    return new_val if new_val != val else val

def clean_thousands_separator(val):
    """القاعدة 3: إزالة فواصل الآلاف"""
    if not isinstance(val, str): return val
    # التحقق من وجود نمط أرقام مع فواصل (مثل 125,000.00)
    if re.search(r'\d,\d', val):
        new_val = val.replace(',', '')
        return new_val
    return val

def clean_text_prices(val):
    """القاعدة 4: تحويل السعر بالكلمات للقيم المعروفة"""
    if not isinstance(val, str): return val
    text_map = {
        "ألفان": "2000",
        "الفان": "2000",
        "خمسة آلاف": "5000",
        "عشرة آلاف": "10000"
    }
    clean_val = val.strip()
    if clean_val in text_map:
        return text_map[clean_val]
    return val

def clean_phone_number(val):
    """القاعدة 5: توحيد صيغة رقم الهاتف وإزالة المسافات"""
    if not isinstance(val, str): return val
    # إزالة المسافات والشرطات إذا كان يبدأ بمفتاح اليمن
    if '+967' in val or val.startswith('967') or val.startswith('7'):
        new_val = val.replace(' ', '').replace('-', '')
        return new_val if new_val != val else val
    return val

def clean_email(val):
    """القاعدة 6: إصلاح التكرار الواضح في البريد الإلكتروني"""
    if not isinstance(val, str): return val
    new_val = val.replace('@@', '@').replace('..', '.')
    return new_val if new_val != val else val

def clean_date_format(val):
    """القاعدة 7: تحويل التاريخ إلى صيغة قياسية DD/MM/YYYY"""
    if not isinstance(val, str): return val
    # تحويل الشرطات إلى خط مائل
    if re.match(r'\d{2}-\d{2}-\d{4}', val):
        return val.replace('-', '/')
    return val

def clean_spaces_and_synonyms(val):
    """القاعدة 8: إزالة المسافات الزائدة وتوحيد المرادفات للحالة"""
    if not isinstance(val, str): return val
    new_val = " ".join(val.split()) # إزالة المسافات الزائدة
    
    synonyms = {
        "مؤكد": "confirmed",
        "تم التأكيد": "confirmed",
        "مدفوع": "paid",
        "تم الدفع": "paid"
    }
    return synonyms.get(new_val, new_val)

def apply_quality_rules(raw_record):
    """
    تطبيق جميع القواعد على السجل واستخراج أثر التصحيح (Audit Trail)
    """
    cleaned_record = dict(raw_record)
    corrections = []
    
    # خريطة تربط بين الحقول وقواعد التنظيف الخاصة بها
    rules_mapping = {
        'total_amount': [
            (clean_arabic_numbers, "ARABIC_NUMBERS"),
            (clean_currency, "CURRENCY_SYMBOL"),
            (clean_thousands_separator, "THOUSANDS_SEPARATOR"),
            (clean_text_prices, "TEXT_PRICE")
        ],
        'customer_phone': [
            (clean_arabic_numbers, "ARABIC_NUMBERS"),
            (clean_phone_number, "PHONE_FORMAT")
        ],
        'customer_email': [
            (clean_email, "EMAIL_REPEATED_SYMBOLS")
        ],
        'order_date': [
            (clean_date_format, "DATE_FORMAT")
        ],
        'status': [
            (clean_spaces_and_synonyms, "SPACES_AND_SYNONYMS")
        ]
    }
    
    for field, rules in rules_mapping.items():
        if field in cleaned_record and cleaned_record[field]:
            current_val = str(cleaned_record[field])
            
            for rule_func, rule_code in rules:
                new_val = rule_func(current_val)
                if new_val != current_val:
                    corrections.append({
                        "field": field,
                        "original_value": current_val,
                        "corrected_value": new_val,
                        "rule_code": rule_code
                    })
                    current_val = new_val # التحديث لتطبيق القاعدة التالية إن وجدت
            
            cleaned_record[field] = current_val

    # إذا تم إجراء تعديلات، نقوم بتسجيل الحالة كـ corrected
    quality_status = "corrected" if corrections else "valid"
    
    return cleaned_record, quality_status, corrections

# كود اختباري بسيط للتحقق من عمل القواعد
if __name__ == "__main__":
    test_record = {
        "order_id": "1001",
        "total_amount": "٥٠٠٠ ريال",
        "customer_phone": "+967 77 123 4567",
        "customer_email": "user@@mail..com",
        "order_date": "31-01-2025",
        "status": " تم التأكيد "
    }
    
    print("السجل الأصلي:")
    print(test_record)
    
    cleaned, status, trail = apply_quality_rules(test_record)
    
    print("\nحالة الجودة:", status)
    print("السجل المنظف:")
    print(cleaned)
    print("\nأثر التصحيح (Audit Trail):")
    for t in trail:
        print(t)