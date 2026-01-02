# Ai_project/core_ai/urls.py
from django.urls import path, include
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from core_ai.views.codefile import CodeFileViewSet
from core_ai.views.analysis import AnalysisJobViewSet, AnalysisResultViewSet
from core_ai.views.ai_explanation import AIExplanationViewSet, export_explanation_file
from core_ai.views.logic_explanation import LogicExplanationViewSet

router = DefaultRouter()
router.register(r'codefiles', CodeFileViewSet, basename='codefile') # <<< أضف basename
router.register(r'analysis-jobs', AnalysisJobViewSet, basename='analysis-job') # <<< أضف basename
router.register(r'analysis-results', AnalysisResultViewSet, basename='analysis-result') # <<< أضف basename
# router.register(r'ai-explanations', AIExplanationViewSet, basename='ai-explanations')  # Disabled to avoid conflict with export URL

urlpatterns = [
    # مسار debug
    path('test/', lambda request: HttpResponse('Test route works'), name='test-route'),
    path('ai-explanations/test/', lambda request: HttpResponse('AI explanations test works'), name='ai-test-route'),
    # مسار تصدير ملفات الشروحات - ضعه أولاً
    path('ai-explanations/<str:explanation_id>/export-file/', export_explanation_file, name='export-explanation-file'),
    path('ai-explanations/debug/', lambda request: HttpResponse('Export path works'), name='export-debug'),
    # مسار قائمة الشروحات
    path('ai-explanations/', AIExplanationViewSet.as_view({'get': 'list'}), name='ai-explanations-list'),
    # مسارات شرح المنطق
    path('logic-explanation/explain/', LogicExplanationViewSet.as_view({'post': 'explain_logic'}), name='logic-explanation-explain'),
    path('logic-explanation/levels/', LogicExplanationViewSet.as_view({'get': 'get_levels'}), name='logic-explanation-levels'),
    path('logic-explanation/project-files/', LogicExplanationViewSet.as_view({'get': 'get_project_files'}), name='logic-explanation-project-files'),
    path('', include(router.urls)),
]
