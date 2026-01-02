"""
Repository Pattern Classes - طبقة الوصول للبيانات
تحتوي على classes مسؤولة عن التعامل مع قاعدة البيانات

أنواع الـ Repositories:
- AITask: إدارة مهام الذكاء الاصطناعي
- analyze_code_file_task2: مهمة Celery لتحليل الكود
"""

from .ai_task import AITask

try:
    from .analyze_code import analyze_code_file_task2
    _celery_tasks = [analyze_code_file_task2]
except ImportError:
    _celery_tasks = []

__all__ = ['AITask', 'analyze_code_file_task2']
