import unittest
import sys
import os

# ربط المسار للوصول إلى مجلد src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from quality_rules import clean_arabic_numbers, clean_phone_number, clean_email

class TestCleaningRules(unittest.TestCase):
    
    def test_clean_arabic_numbers(self):
        """اختبار تحويل الأرقام العربية إلى لاتينية"""
        self.assertEqual(clean_arabic_numbers("٥٠٠٠"), "5000")
        self.assertEqual(clean_arabic_numbers("123"), "123")

    def test_clean_phone_number(self):
        """اختبار إزالة المسافات من رقم الهاتف"""
        self.assertEqual(clean_phone_number("+967 77 123 4567"), "+967771234567")

    def test_clean_email(self):
        """اختبار إصلاح التكرار في البريد الإلكتروني"""
        self.assertEqual(clean_email("user@@mail..com"), "user@mail.com")

if __name__ == '__main__':
    unittest.main()