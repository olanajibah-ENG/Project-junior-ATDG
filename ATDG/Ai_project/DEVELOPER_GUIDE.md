# دليل المطور - توسعة النظام

## 🎯 نظرة عامة
هذا الدليل موجه للمطورين الذين يريدون إضافة ميزات جديدة أو تطوير النظام.

## 🏗️ معمارية النظام

### نمط الطبقات (Layered Architecture)
```
┌─────────────────────────────────────┐
│           API Layer                 │  ← Django REST Framework
├─────────────────────────────────────┤
│         Business Logic              │  ← Orchestrator + Agents
├─────────────────────────────────────┤
│       Language Processors          │  ← AST + Tree-sitter
├─────────────────────────────────────┤
│         Data Layer                  │  ← MongoDB + Pydantic
└─────────────────────────────────────┘
```

### نمط الاستراتيجية (Strategy Pattern)
```python
# واجهة موحدة لجميع معالجات اللغات
class ILanguageProcessorStrategy(ABC):
    @abstractmethod
    def parse_source_code(self, code_content: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
```

## 🔧 إضافة لغة برمجة جديدة

### الخطوة 1: إنشاء معالج جديد

```python
# core_ai/language_processors/javascript_processor.py
from .base_processor import ILanguageProcessorStrategy
import tree_sitter_javascript as ts_js
from tree_sitter import Language, Parser

class JavaScriptProcessor(ILanguageProcessorStrategy):
    def __init__(self):
        # إعداد Tree-sitter للـ JavaScript
        JS_LANGUAGE = Language(ts_js.language(), "javascript")
        self.parser = Parser()
        self.parser.set_language(JS_LANGUAGE)
    
    def parse_source_code(self, code_content: str) -> Dict[str, Any]:
        """تحليل كود JavaScript وإرجاع AST"""
        tree = self.parser.parse(bytes(code_content, "utf8"))
        
        return {
            "classes": self._extract_classes(tree.root_node),
            "functions": self._extract_functions(tree.root_node),
            "imports": self._extract_imports(tree.root_node),
            "exports": self._extract_exports(tree.root_node),
            "code_content": code_content
        }
    
    def _extract_classes(self, node):
        """استخراج الكلاسات من AST"""
        classes = []
        
        def traverse(node):
            if node.type == "class_declaration":
                class_name = self._get_class_name(node)
                methods = self._get_class_methods(node)
                
                classes.append({
                    "name": class_name,
                    "methods": methods,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1,
                    "associations": self._detect_associations(node)
                })
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return classes
    
    def _extract_functions(self, node):
        """استخراج الدوال من AST"""
        functions = []
        
        def traverse(node):
            if node.type in ["function_declaration", "arrow_function"]:
                func_name = self._get_function_name(node)
                parameters = self._get_function_parameters(node)
                
                functions.append({
                    "name": func_name,
                    "parameters": parameters,
                    "line_start": node.start_point[0] + 1,
                    "line_end": node.end_point[0] + 1
                })
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return functions
    
    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        """استخراج الميزات الإحصائية"""
        code_lines = ast_data["code_content"].split('\n')
        
        return {
            "lines_of_code": len([line for line in code_lines if line.strip()]),
            "number_of_classes": len(ast_data["classes"]),
            "number_of_functions": len(ast_data["functions"]),
            "number_of_methods": sum(len(cls["methods"]) for cls in ast_data["classes"]),
            "imports_count": len(ast_data["imports"]),
            "exports_count": len(ast_data["exports"]),
            "design_patterns": self._detect_design_patterns(ast_data)
        }
    
    def _detect_design_patterns(self, ast_data):
        """كشف أنماط التصميم في JavaScript"""
        patterns = []
        
        # كشف Module Pattern
        if ast_data["exports"]:
            patterns.append("Module Pattern")
        
        # كشف Singleton Pattern
        for cls in ast_data["classes"]:
            if self._is_singleton_class(cls):
                patterns.append("Singleton Pattern")
        
        # كشف Factory Pattern
        for func in ast_data["functions"]:
            if "create" in func["name"].lower() or "factory" in func["name"].lower():
                patterns.append("Factory Pattern")
        
        return patterns
```

### الخطوة 2: تحديث المتطلبات

```bash
# إضافة إلى requirements.txt
tree-sitter-javascript>=0.20.0
```

### الخطوة 3: تسجيل المعالج الجديد

```python
# core_ai/language_processors/__init__.py
from .python_processor import PythonProcessor
from .java_processor import JavaProcessor
from .javascript_processor import JavaScriptProcessor  # جديد

LANGUAGE_PROCESSORS = {
    'python': PythonProcessor,
    'java': JavaProcessor,
    'javascript': JavaScriptProcessor,  # جديد
    'js': JavaScriptProcessor,  # اختصار
}

def get_processor(file_type: str):
    processor_class = LANGUAGE_PROCESSORS.get(file_type.lower())
    if not processor_class:
        raise ValueError(f"Unsupported language: {file_type}")
    return processor_class()
```

### الخطوة 4: اختبار المعالج الجديد

```python
# tests/test_javascript_processor.py
import unittest
from core_ai.language_processors.javascript_processor import JavaScriptProcessor

class TestJavaScriptProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = JavaScriptProcessor()
    
    def test_class_extraction(self):
        code = """
        class Car {
            constructor(model) {
                this.model = model;
                this.engine = new Engine();
            }
            
            drive() {
                return this.engine.start();
            }
        }
        """
        
        result = self.processor.parse_source_code(code)
        
        self.assertEqual(len(result["classes"]), 1)
        self.assertEqual(result["classes"][0]["name"], "Car")
        self.assertEqual(len(result["classes"][0]["methods"]), 2)
    
    def test_function_extraction(self):
        code = """
        function createCar(model) {
            return new Car(model);
        }
        
        const startEngine = () => {
            console.log("Engine started");
        };
        """
        
        result = self.processor.parse_source_code(code)
        
        self.assertEqual(len(result["functions"]), 2)
        self.assertIn("createCar", [f["name"] for f in result["functions"]])
```

## 🤖 إضافة وكيل ذكاء اصطناعي جديد

### مثال: وكيل تحليل الأمان

```python
# core_ai/ai_engine/security_agent.py
from .agents import BaseAgent

class SecurityAgent(BaseAgent):
    def analyze_security_issues(self, code_content, ast_data):
        """تحليل المشاكل الأمنية في الكود"""
        
        system_prompt = """
        أنت خبير أمان تطبيقات مع 10+ سنوات خبرة. مهمتك تحليل الكود 
        والبحث عن الثغرات الأمنية المحتملة.
        
        ركز على:
        - SQL Injection vulnerabilities
        - XSS vulnerabilities  
        - Authentication issues
        - Input validation problems
        - Hardcoded secrets
        - Insecure configurations
        
        قدم تقرير مفصل مع:
        1. مستوى الخطورة (High/Medium/Low)
        2. وصف المشكلة
        3. الحل المقترح
        4. مثال على الكود الآمن
        """
        
        user_prompt = f"""
        تحليل الكود التالي للثغرات الأمنية:
        
        معلومات الهيكل:
        - عدد الكلاسات: {len(ast_data.get('classes', []))}
        - عدد الدوال: {len(ast_data.get('functions', []))}
        
        الكود:
        {code_content}
        
        قدم تقرير أمان شامل.
        """
        
        return self.ask_ai(system_prompt, user_prompt)
```

### تحديث الـ Orchestrator

```python
# في core_ai/ai_engine/orchestrator.py
from .security_agent import SecurityAgent

class DocumentationOrchestrator:
    def get_security_analysis(self, analysis_id):
        """توليد تحليل أمان للكود"""
        
        # التحقق من وجود تحليل أمان سابق
        existing = self.collection.find_one({
            "analysis_id": ObjectId(analysis_id),
            "explanation_type": "security_analysis"
        })
        
        if existing:
            return existing['content'], str(existing['_id'])
        
        # جلب بيانات التحليل
        analysis_data = self.db[settings.ANALYSIS_RESULTS_COLLECTION].find_one(
            {"_id": ObjectId(analysis_id)}
        )
        
        if not analysis_data:
            raise Exception("Analysis record not found.")
        
        # تشغيل وكيل الأمان
        security_agent = SecurityAgent()
        security_report = security_agent.analyze_security_issues(
            analysis_data['ast_structure']['code_content'],
            analysis_data['ast_structure']
        )
        
        # حفظ النتيجة
        explanation_doc = {
            "analysis_id": ObjectId(analysis_id),
            "explanation_type": "security_analysis",
            "content": security_report,
            "created_at": datetime.utcnow()
        }
        
        result = self.collection.insert_one(explanation_doc)
        return security_report, str(result.inserted_id)
```

## 📊 إضافة مولد تقارير جديد

### مثال: مولد تقرير Excel

```python
# core_ai/ai_engine/doc/excel_generator.py
import pandas as pd
from io import BytesIO
from .doc_generator import DocumentationGenerator

class ExcelGenerator(DocumentationGenerator):
    """مولد تقارير Excel مع جداول وإحصائيات"""
    
    def _build_content(self, data):
        """بناء المحتوى كـ DataFrame"""
        analysis_data = data.get('analysis_data', {})
        
        # جدول الكلاسات
        classes_df = pd.DataFrame([
            {
                'Class Name': cls['name'],
                'Methods Count': len(cls['methods']),
                'Line Start': cls['line_start'],
                'Line End': cls['line_end'],
                'Associations': len(cls.get('associations', []))
            }
            for cls in analysis_data.get('classes', [])
        ])
        
        # جدول الدوال
        functions_df = pd.DataFrame([
            {
                'Function Name': func['name'],
                'Parameters': len(func['parameters']),
                'Line Start': func['line_start'],
                'Line End': func['line_end']
            }
            for func in analysis_data.get('functions', [])
        ])
        
        # إحصائيات عامة
        features = analysis_data.get('features', {})
        stats_df = pd.DataFrame([
            {'Metric': 'Lines of Code', 'Value': features.get('lines_of_code', 0)},
            {'Metric': 'Classes', 'Value': features.get('number_of_classes', 0)},
            {'Metric': 'Functions', 'Value': features.get('number_of_functions', 0)},
            {'Metric': 'Methods', 'Value': features.get('number_of_methods', 0)},
            {'Metric': 'Complexity', 'Value': features.get('cyclomatic_complexity', 0)}
        ])
        
        return {
            'classes': classes_df,
            'functions': functions_df,
            'statistics': stats_df,
            'explanation': data.get('content', '')
        }
    
    def _format_output(self, content_dict, data):
        """تنسيق وإنشاء ملف Excel"""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # كتابة الجداول في sheets منفصلة
            content_dict['statistics'].to_excel(
                writer, sheet_name='Statistics', index=False
            )
            content_dict['classes'].to_excel(
                writer, sheet_name='Classes', index=False
            )
            content_dict['functions'].to_excel(
                writer, sheet_name='Functions', index=False
            )
            
            # إضافة الشرح كنص
            explanation_df = pd.DataFrame([{'AI Explanation': content_dict['explanation']}])
            explanation_df.to_excel(
                writer, sheet_name='AI Analysis', index=False
            )
        
        output.seek(0)
        return output.getvalue()
```

## 🔌 إضافة API endpoint جديد

### مثال: endpoint للإحصائيات المتقدمة

```python
# core_ai/views/analytics_views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Avg
from core_ai.mongo_utils import get_mongo_db
from datetime import datetime, timedelta

@api_view(['GET'])
def advanced_analytics(request):
    """إحصائيات متقدمة للنظام"""
    
    db = get_mongo_db()
    
    # إحصائيات الملفات حسب اللغة
    pipeline = [
        {"$group": {
            "_id": "$file_type",
            "count": {"$sum": 1},
            "avg_size": {"$avg": {"$strLenCP": "$content"}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    files_by_language = list(db.code_files.aggregate(pipeline))
    
    # إحصائيات التحليلات الناجحة
    success_rate = db.analysis_results.count_documents({"status": "COMPLETED"})
    total_analyses = db.analysis_results.count_documents({})
    
    # أكثر أنماط التصميم استخداماً
    pipeline = [
        {"$unwind": "$features.design_patterns"},
        {"$group": {
            "_id": "$features.design_patterns",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    popular_patterns = list(db.analysis_results.aggregate(pipeline))
    
    # إحصائيات الاستخدام اليومي
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_usage = db.ai_explanations.count_documents({
        "created_at": {"$gte": today}
    })
    
    return Response({
        "files_by_language": files_by_language,
        "success_rate": (success_rate / total_analyses * 100) if total_analyses > 0 else 0,
        "popular_design_patterns": popular_patterns,
        "daily_ai_requests": daily_usage,
        "cache_efficiency": _calculate_cache_efficiency(),
        "system_health": _get_system_health()
    })

def _calculate_cache_efficiency():
    """حساب كفاءة التخزين المؤقت"""
    db = get_mongo_db()
    
    # عدد الطلبات التي استخدمت cache
    cached_requests = db.ai_explanations.count_documents({
        "created_at": {"$gte": datetime.now() - timedelta(days=7)}
    })
    
    # إجمالي الطلبات
    total_requests = db.analysis_jobs.count_documents({
        "created_at": {"$gte": datetime.now() - timedelta(days=7)}
    })
    
    return (cached_requests / total_requests * 100) if total_requests > 0 else 0

def _get_system_health():
    """فحص صحة النظام"""
    try:
        db = get_mongo_db()
        # اختبار الاتصال بقاعدة البيانات
        db.command("ping")
        
        # اختبار الـ AI service
        from core_ai.ai_engine.llm_client import GeminiClient
        # يمكن إضافة اختبار بسيط هنا
        
        return {
            "database": "healthy",
            "ai_service": "healthy",
            "overall": "healthy"
        }
    except Exception as e:
        return {
            "database": "error",
            "ai_service": "unknown",
            "overall": "degraded",
            "error": str(e)
        }
```

### إضافة الـ URL

```python
# في core_ai/urls.py
from core_ai.views.analytics_views import advanced_analytics

urlpatterns = [
    # ... الـ URLs الموجودة
    path('analytics/advanced/', advanced_analytics, name='advanced-analytics'),
]
```

## 🧪 كتابة الاختبارات

### اختبار وحدة للمعالج

```python
# tests/test_processors.py
import unittest
from core_ai.language_processors import get_processor

class TestLanguageProcessors(unittest.TestCase):
    
    def test_python_processor(self):
        processor = get_processor('python')
        
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
        """
        
        result = processor.parse_source_code(code)
        
        self.assertEqual(len(result['classes']), 1)
        self.assertEqual(result['classes'][0]['name'], 'Calculator')
        self.assertEqual(len(result['classes'][0]['methods']), 2)
    
    def test_unsupported_language(self):
        with self.assertRaises(ValueError):
            get_processor('unsupported_language')
```

### اختبار تكامل للـ API

```python
# tests/test_api_integration.py
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User

class APIIntegrationTest(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_upload_and_analyze_flow(self):
        # تسجيل الدخول
        self.client.force_authenticate(user=self.user)
        
        # رفع ملف
        response = self.client.post('/api/codefiles/', {
            'filename': 'test.py',
            'file_type': 'python',
            'content': 'def hello(): return "Hello World"'
        })
        
        self.assertEqual(response.status_code, 201)
        file_id = response.data['id']
        
        # بدء التحليل
        response = self.client.post(f'/api/codefiles/{file_id}/analyze/')
        self.assertEqual(response.status_code, 202)
        
        # التحقق من النتيجة (بعد انتظار المعالجة)
        # في الاختبار الحقيقي، ستحتاج لمحاكاة Celery task
```

## 📈 مراقبة الأداء

### إضافة logging مفصل

```python
# core_ai/utils/performance_monitor.py
import logging
import time
from functools import wraps

logger = logging.getLogger('performance')

def monitor_performance(operation_name):
    """Decorator لمراقبة أداء العمليات"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"{operation_name} completed in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{operation_name} failed after {execution_time:.2f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator

# الاستخدام
@monitor_performance("Code Analysis")
def analyze_code(code_content):
    # منطق التحليل
    pass
```

## 🚀 نشر التحديثات

### إعداد CI/CD بسيط

```yaml
# .github/workflows/deploy.yml
name: Deploy AI Documentation System

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python manage.py test
    
    - name: Run linting
      run: |
        flake8 core_ai/
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Deploy to production
      run: |
        # خطوات النشر هنا
        echo "Deploying to production..."
```

## 📝 أفضل الممارسات

### 1. تنظيم الكود
- استخدم Type Hints في Python
- اتبع PEP 8 للتنسيق
- أضف docstrings لجميع الدوال

### 2. معالجة الأخطاء
- استخدم try-catch مع logging مفصل
- أرجع رسائل خطأ واضحة للمستخدم
- تجنب كشف تفاصيل النظام الداخلية

### 3. الأداء
- استخدم caching للعمليات المكلفة
- راقب استهلاك الذاكرة في معالجة الملفات الكبيرة
- استخدم async/await للعمليات I/O

### 4. الأمان
- تحقق من صحة جميع المدخلات
- استخدم parameterized queries
- لا تحفظ API keys في الكود

---
**هذا الدليل يتطور مع النظام. ساهم في تحسينه!**