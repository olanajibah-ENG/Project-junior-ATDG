# 🚀 Ai_project - نظام الذكاء الاصطناعي الأساسي

المشروع الرئيسي لتحليل وتوثيق الكود البرمجي باستخدام Django و MongoDB والذكاء الاصطناعي المجاني.

## 🏗️ هيكل المشروع

```
Ai_project/
├── 📄 README.md                    # دليل هذا المشروع
├── 🐳 Dockerfile                  # حاوية Docker
├── 📄 entrypoint.sh              # سكريبت بدء الخدمة
├── 📄 requirements.txt           # متطلبات Python
├── 📄 manage.py                  # أداة إدارة Django
├── 📁 Ai_project/                # إعدادات Django الرئيسية
│   ├── settings.py              # إعدادات المشروع
│   ├── urls.py                  # مسارات URL الرئيسية
│   └── celery_app.py            # إعدادات Celery
└── 📁 core_ai/                   # التطبيق الأساسي للتحليل
    ├── models.py                # نماذج البيانات (MongoDB)
    ├── views.py                 # API endpoints
    ├── serializers.py           # تسلسل البيانات
    ├── urls.py                  # مسارات API
    ├── analyze_code.py          # منطق تحليل الكود
    └── language_processors/     # معالجات اللغات
        ├── base_processor.py    # المعالج الأساسي
        ├── python_processor.py  # معالج Python
        └── java_processor.py    # معالج Java
```

## 🚀 الميزات الرئيسية

### تحليل الكود الآلي
- **لغات مدعومة**: Python, Java
- **استخراج الميزات**: عدد الأسطر، الدوال، المتغيرات
- **تحليل التركيب**: علاقات Composition بين الفئات (يعمل لكلا اللغتين)
- **خرائط التبعيات**: تحليل الاعتماديات بين الملفات
- **مخططات الفئات**: استخراج شامل للفئات والعلاقات

### API شامل
- **إدخال متعدد**: JSON أو رفع ملفات
- **معالجة غير متزامنة**: Celery للمهام الثقيلة
- **تخزين MongoDB**: قاعدة بيانات NoSQL
- **REST API**: واجهة RESTful كاملة

## 🔧 الإعداد والتشغيل

### متطلبات النظام
- Python 3.10+
- MongoDB
- Redis
- Docker (اختياري)

### خطوات التشغيل

1. **تثبيت المتطلبات**
   ```bash
   pip install -r requirements.txt
   ```

2. **إعداد قاعدة البيانات**
   ```bash
   # MongoDB يجب أن يكون متاحاً
   # Redis يجب أن يكون متاحاً
   ```

3. **تشغيل الخدمة**
   ```bash
   # تشغيل خادم Django
   python manage.py runserver 0.0.0.0:8000

   # تشغيل Celery worker
   celery -A Ai_project.celery_app worker -l INFO
   ```

## 📡 API Endpoints

### إدارة ملفات الكود
```
POST   /api/analysis/codefiles/           # إنشاء ملف كود جديد
GET    /api/analysis/codefiles/           # سرد جميع ملفات الكود
GET    /api/analysis/codefiles/{id}/      # تفاصيل ملف كود محدد
```

### نتائج التحليل
```
GET    /api/analysis/analysis-results/{id}/ # نتائج تحليل ملف كود
```

### أمثلة الاستخدام

#### إرسال كود Python عبر JSON
```bash
curl -X POST http://localhost:8002/api/analysis/codefiles/ \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "example.py",
    "file_type": "python",
    "content": "class Car:\n    def __init__(self):\n        self.engine = Engine()"
  }'
```

#### رفع ملف كود
```bash
curl -X POST http://localhost:8002/api/analysis/codefiles/ \
  -F "filename=example.py" \
  -F "file_type=python" \
  -F "uploaded_file=@example.py"
```

## 🔍 نتائج التحليل

### بيانات مخطط الفئات (Class Diagram)
```json
{
  "classes": [
    {
      "name": "Car",
      "methods": ["__init__(self)", "drive(self)"],
      "associations": [
        {
          "target_class": "Engine",
          "type": "Composition",
          "attribute": "engine"
        }
      ]
    }
  ]
}
```

### الميزات المستخرجة
```json
{
  "lines_of_code": 25,
  "functions": 3,
  "classes": 2
}
```

## 🧪 الاختبارات

### تشغيل الاختبارات
```bash
# من المجلد الجذر للمشروع
python tests/simple_final_test.py
```

### اختبارات محددة
```bash
python tests/test_api_simple.py    # اختبار API
python tests/check_analysis.py     # فحص النتائج
```

## 🔧 استكشاف الأخطاء

### مشاكل شائعة

1. **فشل تحليل Java**
   ```
   Error: Java parser not initialized
   ```
   **الحل**: تأكد من تثبيت tree-sitter-languages

2. **مشاكل Celery**
   ```
   # فحص logs Celery
   docker-compose logs celery_worker

   # إعادة تشغيل Celery
   docker-compose restart celery_worker
   ```

3. **مشاكل MongoDB**
   ```
   # فحص اتصال MongoDB
   python manage.py shell
   >>> from core_ai.mongo_utils import get_mongo_db
   >>> db = get_mongo_db()
   >>> print(db.list_collection_names())
   ```

## 📚 المراجع

- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [MongoDB Python Driver](https://pymongo.readthedocs.io/)

## 👥 المساهمون

- [اسم المطور]

---

**ملاحظة**: هذه الخدمة تعمل كميكروسيرفس منفصل ضمن نظام UPM الأكبر.