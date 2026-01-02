import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from core_ai.ai_engine.llm_client import GeminiClient
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class LogicExplanationViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def explain_logic(self, request):
        """
        شرح منطق الكود بمستويين: high_level و low_level
        """
        try:
            # استخراج البيانات من الطلب
            code_content = request.data.get('code_content', '')
            explanation_level = request.data.get('level', 'high_level')  # high_level أو low_level
            code_name = request.data.get('code_name', 'unknown')
            file_name = request.data.get('file_name', 'unknown')

            if not code_content:
                return Response({
                    'error': 'رمز الكود مطلوب',
                    'message': 'يجب إرسال محتوى الكود لشرح منطقه'
                }, status=status.HTTP_400_BAD_REQUEST)

            if explanation_level not in ['high_level', 'low_level']:
                return Response({
                    'error': 'مستوى شرح غير صحيح',
                    'message': 'يجب أن يكون المستوى إما high_level أو low_level'
                }, status=status.HTTP_400_BAD_REQUEST)

            # استخدام GeminiClient مباشرة للشرح

            # إعداد الـ prompt حسب المستوى
            if explanation_level == 'high_level':
                prompt = f"""
                شرح هذا الكود بطريقة بسيطة جداً:

                {code_content}

                قل لي:
                - ماذا يفعل هذا الكود؟
                - ما هو الغرض منه؟
                - ما هي المكونات الأساسية؟

                استخدم لغة عربية بسيطة كأنك تشرح لطفل.
                """
            else:  # low_level
                prompt = f"""
                شرح هذا الكود بالتفصيل:

                {code_content}

                قل لي:
                - كيف تعمل كل دالة بالضبط؟
                - ما هو تدفق البيانات؟
                - ما هي الخوارزميات المستخدمة؟
                - كيف تتفاعل الأجزاء مع بعضها؟

                استخدم لغة عربية تقنية دقيقة.
                """

            # إرسال الطلب للذكاء الاصطناعي
            explanation_result = GeminiClient.call_gemini(
                system_prompt="أنت مساعد متخصص في شرح أكواد البرمجة باللغة العربية. ركز على الشرح الواضح والمفيد.",
                user_prompt=prompt
            )

            # تنسيق النتيجة
            result = {
                'code_name': code_name,
                'file_name': file_name,
                'explanation_level': explanation_level,
                'level_display': 'عالي المستوى' if explanation_level == 'high_level' else 'منخفض المستوى',
                'explanation': explanation_result,
                'code_preview': code_content[:500] + '...' if len(code_content) > 500 else code_content,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'code_length': len(code_content),
                    'level': explanation_level,
                    'model_used': 'openrouter',  # أو أي model آخر
                }
            }

            logger.info(f"Logic explanation generated for {code_name} at {explanation_level} level")

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in logic explanation: {str(e)}")
            return Response({
                'error': 'خطأ في شرح المنطق',
                'message': f'حدث خطأ أثناء شرح منطق الكود: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_levels(self, request):
        """
        إرجاع المستويات المتاحة لشرح المنطق
        """
        levels = [
            {
                'id': 'high_level',
                'name': 'شرح بسيط',
                'description': 'ماذا يفعل الكود؟',
                'icon': '💡',
                'suitable_for': 'الجميع'
            },
            {
                'id': 'low_level',
                'name': 'شرح مفصل',
                'description': 'كيف يعمل الكود بالتفصيل؟',
                'icon': '⚙️',
                'suitable_for': 'المطورين'
            }
        ]

        return Response(levels, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def get_project_files(self, request):
        """
        إرجاع ملفات الكود المتاحة للمشاريع
        """
        try:
            # هنا يمكنك إضافة منطق لجلب الملفات من قاعدة البيانات
            # أو من ملفات تم تحليلها سابقاً

            # للآن سنرجع بيانات تجريبية
            sample_files = [
                {
                    'id': '1',
                    'project_id': request.query_params.get('project_id', '1'),
                    'file_name': 'UserService.java',
                    'language': 'java',
                    'size': 2456,
                    'last_modified': '2024-12-19T10:30:00Z',
                    'code_preview': 'public class UserService {\n    private UserRepository userRepo;\n\n    public UserService(UserRepository userRepo) {\n        this.userRepo = userRepo;\n    }\n\n    public User createUser(String username, String email) {\n        // Implementation\n    }\n}',
                    'status': 'analyzed'
                },
                {
                    'id': '2',
                    'project_id': request.query_params.get('project_id', '1'),
                    'file_name': 'PaymentProcessor.py',
                    'language': 'python',
                    'size': 1834,
                    'last_modified': '2024-12-19T09:15:00Z',
                    'code_preview': 'class PaymentProcessor:\n    def __init__(self, payment_gateway):\n        self.gateway = payment_gateway\n\n    def process_payment(self, amount, currency):\n        """Process a payment transaction"""\n        return self.gateway.charge(amount, currency)',
                    'status': 'analyzed'
                },
                {
                    'id': '3',
                    'project_id': request.query_params.get('project_id', '2'),
                    'file_name': 'DatabaseManager.java',
                    'language': 'java',
                    'size': 3124,
                    'last_modified': '2024-12-18T16:45:00Z',
                    'code_preview': 'public class DatabaseManager {\n    private Connection connection;\n\n    public DatabaseManager() {\n        this.connection = DriverManager.getConnection("jdbc:mysql://localhost:3306/mydb");\n    }\n\n    public ResultSet executeQuery(String sql) {\n        return connection.createStatement().executeQuery(sql);\n    }\n}',
                    'status': 'analyzed'
                }
            ]

            return Response(sample_files, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting project files: {str(e)}")
            return Response({
                'error': 'خطأ في جلب ملفات المشروع',
                'message': f'حدث خطأ أثناء جلب ملفات المشروع: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
