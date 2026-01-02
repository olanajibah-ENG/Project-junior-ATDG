# دليل API - نظام توليد التوثيق التلقائي

## 🌐 نظرة عامة على API

Base URL: `http://localhost:8000/api/`

جميع الـ endpoints تستخدم JSON format وتتطلب Content-Type: application/json

## 🔐 المصادقة

النظام يدعم JWT authentication:

```bash
# الحصول على token
POST /api/auth/login/
{
    "username": "your_username",
    "password": "your_password"
}

# استخدام token في الطلبات
Authorization: Bearer your_jwt_token_here
```

## 📁 إدارة ملفات الكود

### 1. رفع ملف كود جديد

**Endpoint:** `POST /api/codefiles/`

**الطرق المدعومة:**
- رفع ملف مباشرة
- إدخال الكود كنص

```bash
# طريقة 1: رفع ملف
curl -X POST http://localhost:8000/api/codefiles/ \
  -H "Content-Type: multipart/form-data" \
  -F "uploaded_file=@example.py" \
  -F "file_type=python"

# طريقة 2: إدخال نص مباشر
curl -X POST http://localhost:8000/api/codefiles/ \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "car_example.py",
    "file_type": "python",
    "content": "class Car:\n    def __init__(self, model):\n        self.model = model\n        self.engine = Engine()\n    \n    def drive(self):\n        return self.engine.start()"
  }'
```

**Response:**
```json
{
    "id": "60f7b1c8e4b0c8a2d8f9e1a2",
    "filename": "car_example.py",
    "file_type": "python",
    "uploaded_at": "2024-01-15T10:30:00Z",
    "analysis_status": "PENDING",
    "source_project_id": null
}
```

### 2. استعراض ملفات الكود

**Endpoint:** `GET /api/codefiles/`

```bash
curl -X GET http://localhost:8000/api/codefiles/
```

**Response:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/codefiles/?page=2",
    "previous": null,
    "results": [
        {
            "id": "60f7b1c8e4b0c8a2d8f9e1a2",
            "filename": "car_example.py",
            "file_type": "python",
            "uploaded_at": "2024-01-15T10:30:00Z",
            "analysis_status": "COMPLETED"
        }
    ]
}
```

### 3. الحصول على ملف محدد

**Endpoint:** `GET /api/codefiles/{id}/`

```bash
curl -X GET http://localhost:8000/api/codefiles/60f7b1c8e4b0c8a2d8f9e1a2/
```

## 🔍 عمليات التحليل

### 1. بدء تحليل جديد

**Endpoint:** `POST /api/analysis-jobs/`

```bash
curl -X POST http://localhost:8000/api/codefiles/60f7b1c8e4b0c8a2d8f9e1a2/analyze/ \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
    "job_id": "60f7b1c8e4b0c8a2d8f9e1a3",
    "code_file_id": "60f7b1c8e4b0c8a2d8f9e1a2",
    "status": "PENDING",
    "created_at": "2024-01-15T10:35:00Z"
}
```

### 2. متابعة حالة التحليل

**Endpoint:** `GET /api/analysis-jobs/{job_id}/`

```bash
curl -X GET http://localhost:8000/api/analysis-jobs/60f7b1c8e4b0c8a2d8f9e1a3/
```

**Response:**
```json
{
    "job_id": "60f7b1c8e4b0c8a2d8f9e1a3",
    "code_file_id": "60f7b1c8e4b0c8a2d8f9e1a2",
    "status": "COMPLETED",
    "created_at": "2024-01-15T10:35:00Z",
    "started_at": "2024-01-15T10:35:05Z",
    "completed_at": "2024-01-15T10:35:45Z",
    "progress": 100
}
```

### 3. الحصول على نتائج التحليل

**Endpoint:** `GET /api/analysis-results/{analysis_id}/`

```bash
curl -X GET http://localhost:8000/api/analysis-results/60f7b1c8e4b0c8a2d8f9e1a4/
```

**Response:**
```json
{
    "analysis_id": "60f7b1c8e4b0c8a2d8f9e1a4",
    "code_file_id": "60f7b1c8e4b0c8a2d8f9e1a2",
    "ast_structure": {
        "classes": [
            {
                "name": "Car",
                "methods": ["__init__", "drive"],
                "line_start": 1,
                "line_end": 8,
                "associations": [
                    {
                        "target_class": "Engine",
                        "type": "Composition",
                        "attribute": "engine"
                    }
                ]
            }
        ],
        "functions": [],
        "imports": ["Engine"],
        "code_content": "class Car:\n    def __init__(self, model):\n        self.model = model\n        self.engine = Engine()\n    \n    def drive(self):\n        return self.engine.start()"
    },
    "features": {
        "lines_of_code": 8,
        "number_of_classes": 1,
        "number_of_methods": 2,
        "number_of_functions": 0,
        "cyclomatic_complexity": 2,
        "design_patterns": ["Composition"]
    },
    "semantic_analysis_data": {
        "dependencies": ["Engine"],
        "class_relationships": {
            "Car": {
                "composes": ["Engine"],
                "inherits_from": [],
                "used_by": []
            }
        }
    },
    "class_diagram_data": {
        "mermaid_syntax": "classDiagram\n    class Car {\n        +model: str\n        +engine: Engine\n        +__init__(model)\n        +drive()\n    }\n    Car *-- Engine : composition"
    }
}
```

## 🤖 الشروحات بالذكاء الاصطناعي

### 1. طلب شرح عالي المستوى (للإدارة)

**Endpoint:** `GET /api/ai-explanations/{analysis_id}/?type=high_level`

```bash
curl -X GET "http://localhost:8000/api/ai-explanations/60f7b1c8e4b0c8a2d8f9e1a4/?type=high_level"
```

**Response:**
```json
{
    "explanation_id": "60f7b1c8e4b0c8a2d8f9e1a5",
    "analysis_id": "60f7b1c8e4b0c8a2d8f9e1a4",
    "explanation_type": "high_level",
    "content": "## Executive Summary\nهذا الكود يمثل نموذج سيارة في نظام محاكاة، حيث تحتوي كل سيارة على محرك وتستطيع القيادة.\n\n## Purpose & Responsibility\nالهدف الرئيسي هو تمثيل كائن السيارة مع إمكانية التحكم في المحرك والقيادة.\n\n## Key Capabilities\n- إنشاء سيارة جديدة مع تحديد الموديل\n- ربط السيارة بمحرك محدد\n- تشغيل المحرك والقيادة\n\n## Business Value\nيستخدم هذا الكود في تطبيقات المحاكاة أو الألعاب التي تتطلب تمثيل مركبات واقعية.",
    "created_at": "2024-01-15T10:40:00Z",
    "cached": false
}
```

### 2. طلب شرح تقني مفصل (للمطورين)

**Endpoint:** `GET /api/ai-explanations/{analysis_id}/?type=low_level`

```bash
curl -X GET "http://localhost:8000/api/ai-explanations/60f7b1c8e4b0c8a2d8f9e1a4/?type=low_level"
```

**Response:**
```json
{
    "explanation_id": "60f7b1c8e4b0c8a2d8f9e1a6",
    "analysis_id": "60f7b1c8e4b0c8a2d8f9e1a4",
    "explanation_type": "low_level",
    "content": "## Technical Implementation\n\n### Class: Car\n\n**Constructor (__init__)**\n- يستقبل معامل model من نوع string\n- ينشئ خاصية self.model لحفظ موديل السيارة\n- ينشئ كائن Engine جديد ويحفظه في self.engine\n- هذا يمثل علاقة Composition بين Car و Engine\n\n**Method: drive()**\n- يستدعي دالة start() من كائن المحرك\n- يعيد النتيجة مباشرة بدون معالجة\n- لا يحتوي على معالجة أخطاء\n- يعتمد على وجود المحرك المُنشأ في Constructor\n\n### Design Patterns\n- **Composition Pattern**: السيارة تحتوي على محرك كجزء منها\n- **Delegation Pattern**: السيارة تفوض عملية التشغيل للمحرك",
    "created_at": "2024-01-15T10:42:00Z",
    "cached": false
}
```

### 3. الحصول على شرح محفوظ

**Endpoint:** `GET /api/cached-documentation/{analysis_id}/`

```bash
curl -X GET http://localhost:8000/api/cached-documentation/60f7b1c8e4b0c8a2d8f9e1a4/
```

## 📄 تصدير التقارير

### 1. تصدير أساسي (PDF أو Markdown)

**Endpoint:** `GET /api/export-file/{explanation_id}/?format=pdf`

```bash
# تصدير PDF
curl -X GET "http://localhost:8000/api/export-file/60f7b1c8e4b0c8a2d8f9e1a5/?format=pdf" \
  --output technical_report.pdf

# تصدير Markdown
curl -X GET "http://localhost:8000/api/export-file/60f7b1c8e4b0c8a2d8f9e1a5/?format=markdown" \
  --output technical_report.md
```

### 2. تصدير PDF مع Class Diagram

**Endpoint:** `GET /api/export-pdf-with-diagram/{explanation_id}/`

```bash
curl -X GET http://localhost:8000/api/export-pdf-with-diagram/60f7b1c8e4b0c8a2d8f9e1a5/ \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/class-diagram.png"}' \
  --output report_with_diagram.pdf
```

### 3. تصدير متقدم مع توليد تلقائي

**Endpoint:** `POST /api/export/`

```bash
curl -X POST http://localhost:8000/api/export/ \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "60f7b1c8e4b0c8a2d8f9e1a4",
    "explanation_type": "high_level",
    "format": "pdf",
    "include_diagram": true,
    "diagram_url": "https://example.com/diagram.png"
  }' \
  --output auto_generated_report.pdf
```

**Response (إذا كان الشرح غير موجود):**
```json
{
    "message": "تم بدء توليد الشرح تلقائياً",
    "task_id": "60f7b1c8e4b0c8a2d8f9e1a7",
    "status": "GENERATING",
    "estimated_time": "30-60 seconds"
}
```

## 📊 إحصائيات ومراقبة

### 1. إحصائيات النظام

**Endpoint:** `GET /api/stats/`

```bash
curl -X GET http://localhost:8000/api/stats/
```

**Response:**
```json
{
    "total_files": 150,
    "total_analyses": 145,
    "total_explanations": 280,
    "success_rate": 96.7,
    "avg_analysis_time": "45 seconds",
    "supported_languages": ["python", "java"],
    "cache_hit_rate": 78.5,
    "api_calls_today": 1250
}
```

### 2. حالة النظام

**Endpoint:** `GET /api/health/`

```bash
curl -X GET http://localhost:8000/api/health/
```

**Response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "ai_service": "available",
    "celery_workers": 3,
    "queue_size": 5,
    "last_check": "2024-01-15T11:00:00Z"
}
```

## ❌ معالجة الأخطاء

### رموز الأخطاء الشائعة

| Code | المعنى | الحل |
|------|--------|------|
| 400 | Bad Request | تحقق من صيغة JSON والمعاملات المطلوبة |
| 401 | Unauthorized | تأكد من صحة JWT token |
| 404 | Not Found | تأكد من صحة ID المرسل |
| 429 | Rate Limited | انتظر قبل إرسال طلبات جديدة |
| 500 | Server Error | خطأ داخلي، تحقق من logs |

### أمثلة على رسائل الأخطاء

```json
{
    "error": "ملف غير مدعوم",
    "message": "نوع الملف 'cpp' غير مدعوم حالياً",
    "supported_types": ["python", "java"],
    "code": "UNSUPPORTED_FILE_TYPE"
}
```

```json
{
    "error": "تحليل فاشل",
    "message": "فشل في تحليل الكود بسبب خطأ في الصيغة",
    "details": "SyntaxError: invalid syntax (line 5)",
    "code": "ANALYSIS_FAILED"
}
```

## 🔧 نصائح للاستخدام الأمثل

### 1. تحسين الأداء
- استخدم cache للشروحات المتكررة
- ارفع ملفات صغيرة (< 10KB) للحصول على أفضل أداء
- استخدم pagination للقوائم الطويلة

### 2. أفضل الممارسات
- أضف معلومات وصفية للملفات (filename, project_id)
- استخدم high_level للمراجعات السريعة
- استخدم low_level للتوثيق التقني المفصل

### 3. استكشاف الأخطاء
- تحقق من logs في حالة فشل التحليل
- تأكد من صحة صيغة الكود قبل الرفع
- استخدم /api/health/ لمراقبة حالة النظام

## 📞 الدعم

للحصول على مساعدة إضافية:
- راجع الـ logs في `/var/log/ai_project/`
- استخدم Django Admin في `/admin/`
- تحقق من حالة Celery workers

---
**آخر تحديث:** يناير 2024