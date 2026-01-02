# Ai_project/core_ai/admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from .mongo_utils import get_mongo_db

# كلاس وهمي (Proxy) لتمكين Django من تسجيله في صفحة الـ Admin
# لأن الـ Admin يبحث دائماً عن Model
class MongoAIExplanation(models.Model):
    analysis_id = models.CharField(max_length=255, blank=True, null=True)
    explanation_type = models.CharField(max_length=100, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "AI Explanation (MongoDB)"
        verbose_name_plural = "AI Explanations (MongoDB)"
        managed = False # مهم جداً لكي لا يحاول Django إنشاء جدول له في SQL

@admin.register(MongoAIExplanation)
class AIExplanationAdmin(admin.ModelAdmin):
    list_display = ('analysis_id_link', 'explanation_type', 'created_at_display')
    readonly_fields = ('analysis_id', 'explanation_type', 'content', 'created_at')

    def get_queryset(self, request):
        # نتركها فارغة لأننا سنجلب البيانات يدوياً
        return super().get_queryset(request)

    def analysis_id_link(self, obj):
        # هذه الدالة فقط لعرض الـ ID بشكل جميل في القائمة
        return str(obj.get('analysis_id', 'N/A'))
    analysis_id_link.short_description = 'Analysis ID'

    def created_at_display(self, obj):
        return obj.get('created_at', 'N/A')
    created_at_display.short_description = 'Created At'

    # تخصيص واجهة العرض لجلب البيانات من MongoDB بدلاً من قاعدة بيانات SQL
    def changelist_view(self, request, extra_context=None):
        db = get_mongo_db()
        # جلب البيانات من كولكشن الشروحات الجديد
        explanations = list(db['ai_explanations'].find().sort('created_at', -1))
        
        extra_context = extra_context or {}
        extra_context['cl'] = {'result_list': explanations, 'title': 'AI Explanations from MongoDB'}
        # ملاحظة: هذا التخصيص يحتاج لتعديل بسيط في قالب (Template) الـ Admin إذا أردتِ عرضاً كاملاً
        return super().changelist_view(request, extra_context=extra_context)