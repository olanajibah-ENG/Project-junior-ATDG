import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny
from django.http import HttpResponse
from bson.objectid import ObjectId
from core_ai.mongo_utils import get_mongo_db
from core_ai.ai_engine.orchestrator import DocumentationOrchestrator
from core_ai.ai_engine.doc.markdown import MarkdownGenerator
from core_ai.ai_engine.doc.pdf import PDFGenerator

logger = logging.getLogger(__name__)

class AIExplanationViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    lookup_field = 'pk'

    def list(self, request):
        """عرض قائمة بجميع الشروحات"""
        try:
            db = get_mongo_db()
            if db is None:
                return Response({
                    "error": "خطأ في الاتصال بقاعدة البيانات",
                    "message": "تعذر الاتصال بقاعدة بيانات MongoDB"
                }, status=500)

            # جلب جميع الشروحات
            documents = list(db['ai_explanations'].find(
                {},
                {
                    '_id': 1,
                    'explanation_type': 1,
                    'created_at': 1,
                    'analysis_id': 1
                }
            ).limit(100))  # حد أقصى 100 وثيقة

            # تحويل ObjectId إلى string للـ JSON
            for doc in documents:
                doc['_id'] = str(doc['_id'])
                if 'analysis_id' in doc and doc['analysis_id']:
                    doc['analysis_id'] = str(doc['analysis_id'])

            return Response(documents)

        except Exception as e:
            logger.error(f"--- [AIExplanationViewSet.list] Error: {str(e)} ---")
            return Response({
                "error": "خطأ في النظام",
                "message": f"حدث خطأ أثناء جلب قائمة الشروحات: {str(e)}"
            }, status=500)

    @action(detail=False, methods=['post'], url_path='generate-explanation')
    def generate_explanation(self, request):
        analysis_id = request.data.get('analysis_id')
        exp_type = request.data.get('type')

        if not analysis_id or not exp_type:
            return Response({"error": "analysis_id and type are required"}, status=400)
            
        if not ObjectId.is_valid(analysis_id):
            return Response({"error": "Invalid analysis_id format"}, status=400)

        try:
            orchestrator = DocumentationOrchestrator(analysis_id=analysis_id)
            content, explanation_id = orchestrator.get_or_generate_explanation(exp_type)
            
            return Response({
                "explanation_id": str(explanation_id),
                "type": exp_type,
                "content": content
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    # 👈 تأكدي أن detail=True موجودة هنا
    @action(detail=True, methods=['get'], url_path='export-file')
    def export_file(self, request, pk=None):
        """
        الرابط المستهدف: /api/analysis/ai-explanations/{ID}/export-file/?format=pdf
        أو: /api/analysis/ai-explanations/export-file/?id={ID}&format=pdf (للتوافق الخلفي)
        """
        logger.info(f"--- [ExportFile] Started for ID: {pk} ---")

        try:
            # التأكد من صحة الـ ID - دعم كل من المسار والـ query parameter
            explanation_id = pk or request.query_params.get('id')

            if not explanation_id:
                logger.warning("--- [ExportFile] Missing ID parameter ---")
                return Response({
                    "error": "معرف الشرح مفقود",
                    "message": "يجب تمرير معرف الشرح في المسار أو كمعامل 'id'"
                }, status=400)

            if not ObjectId.is_valid(explanation_id):
                logger.warning(f"--- [ExportFile] Invalid ObjectId format: {explanation_id} ---")
                return Response({
                    "error": "معرف الشرح غير صحيح",
                    "message": f"المعرف '{explanation_id}' ليس معرف MongoDB صحيح"
                }, status=400)

            format_type = request.query_params.get('format', 'md').lower()
            if format_type not in ['pdf', 'md']:
                logger.warning(f"--- [ExportFile] Unsupported format: {format_type} ---")
                return Response({
                    "error": "صيغة الملف غير مدعومة",
                    "message": "الصيغ المدعومة هي: pdf, md",
                    "supported_formats": ["pdf", "md"]
                }, status=400)

            logger.info(f"--- [ExportFile] Processing ID: {explanation_id}, Format: {format_type} ---")

            # التحقق من الاتصال بقاعدة البيانات
            db = get_mongo_db()
            if db is None:
                logger.error("--- [ExportFile] Database connection failed ---")
                return Response({
                    "error": "خطأ في الاتصال بقاعدة البيانات",
                    "message": "تعذر الاتصال بقاعدة بيانات MongoDB"
                }, status=500)

            # البحث عن البيانات
            data = db['ai_explanations'].find_one({"_id": ObjectId(explanation_id)})

            if not data:
                logger.warning(f"--- [ExportFile] Explanation not found: {explanation_id} ---")
                return Response({
                    "error": "الشرح غير موجود",
                    "message": f"لم يتم العثور على شرح بالمعرف '{explanation_id}'"
                }, status=404)

            logger.info(f"--- [ExportFile] Data found, generating {format_type} file ---")

            # التحقق من وجود المحتوى
            if not data.get('content'):
                logger.warning(f"--- [ExportFile] Empty content for ID: {explanation_id} ---")
                return Response({
                    "error": "المحتوى فارغ",
                    "message": "لا يحتوي الشرح على أي محتوى للتصدير"
                }, status=404)

            # اختيار المولد
            try:
                if format_type == 'pdf':
                    generator = PDFGenerator()
                    content_type = 'application/pdf'
                    filename = f"technical_report_{explanation_id}.pdf"
                else:
                    generator = MarkdownGenerator()
                    content_type = 'text/markdown'
                    filename = f"technical_report_{explanation_id}.md"

                final_file = generator.generate(data)

                if not final_file:
                    logger.error(f"--- [ExportFile] Generator returned empty file ---")
                    return Response({
                        "error": "فشل في توليد الملف",
                        "message": "تعذر توليد ملف التصدير"
                    }, status=500)

                logger.info(f"--- [ExportFile] File generated successfully, size: {len(final_file)} bytes ---")

                response = HttpResponse(final_file, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = len(final_file)

                logger.info(f"--- [ExportFile] Export completed successfully ---")
                return response

            except ImportError as e:
                logger.error(f"--- [ExportFile] Missing dependency: {e} ---")
                return Response({
                    "error": "مكتبة مفقودة",
                    "message": "مكتبة التصدير غير مثبتة بشكل صحيح"
                }, status=500)

            except Exception as e:
                logger.error(f"--- [ExportFile] Generation error: {str(e)} ---")
                return Response({
                    "error": "خطأ في توليد الملف",
                    "message": f"حدث خطأ أثناء توليد ملف {format_type}: {str(e)}"
                }, status=500)

        except Exception as e:
            logger.error(f"--- [ExportFile] Unexpected error: {str(e)} ---")
            return Response({
                "error": "خطأ غير متوقع",
                "message": "حدث خطأ غير متوقع في النظام"
            }, status=500)

    # دعم الطريقة القديمة للتوافق الخلفي
    @action(detail=False, methods=['get'], url_path='export-legacy')
    def export_file_legacy(self, request):
        """
        دعم الرابط القديم: /api/analysis/ai-explanations/export-file/?id={ID}&format=pdf
        """
        logger.info("--- [ExportFileLegacy] Started ---")

        try:
            explanation_id = request.query_params.get('id')
            if not explanation_id:
                logger.warning("--- [ExportFileLegacy] Missing ID parameter ---")
                return Response({
                    "error": "معرف الشرح مفقود",
                    "message": "يجب تمرير معرف الشرح كمعامل 'id'"
                }, status=400)

            if not ObjectId.is_valid(explanation_id):
                logger.warning(f"--- [ExportFileLegacy] Invalid ObjectId: {explanation_id} ---")
                return Response({
                    "error": "معرف الشرح غير صحيح",
                    "message": f"المعرف '{explanation_id}' ليس معرف MongoDB صحيح"
                }, status=400)

            format_type = request.query_params.get('format', 'md').lower()
            if format_type not in ['pdf', 'md']:
                logger.warning(f"--- [ExportFileLegacy] Unsupported format: {format_type} ---")
                return Response({
                    "error": "صيغة الملف غير مدعومة",
                    "message": "الصيغ المدعومة هي: pdf, md"
                }, status=400)

            logger.info(f"--- [ExportFileLegacy] Processing ID: {explanation_id}, Format: {format_type} ---")

            db = get_mongo_db()
            if db is None:
                logger.error("--- [ExportFileLegacy] Database connection failed ---")
                return Response({
                    "error": "خطأ في الاتصال بقاعدة البيانات",
                    "message": "تعذر الاتصال بقاعدة بيانات MongoDB"
                }, status=500)

            data = db['ai_explanations'].find_one({"_id": ObjectId(explanation_id)})

            if not data:
                logger.warning(f"--- [ExportFileLegacy] Data not found: {explanation_id} ---")
                return Response({
                    "error": "الشرح غير موجود",
                    "message": f"لم يتم العثور على شرح بالمعرف '{explanation_id}'"
                }, status=404)

            if not data.get('content'):
                logger.warning(f"--- [ExportFileLegacy] Empty content for ID: {explanation_id} ---")
                return Response({
                    "error": "المحتوى فارغ",
                    "message": "لا يحتوي الشرح على أي محتوى للتصدير"
                }, status=404)

            try:
                if format_type == 'pdf':
                    generator = PDFGenerator()
                    content_type = 'application/pdf'
                    filename = f"technical_report_{explanation_id}.pdf"
                else:
                    generator = MarkdownGenerator()
                    content_type = 'text/markdown'
                    filename = f"technical_report_{explanation_id}.md"

                final_file = generator.generate(data)

                if not final_file:
                    logger.error("--- [ExportFileLegacy] Generator returned empty file ---")
                    return Response({
                        "error": "فشل في توليد الملف",
                        "message": "تعذر توليد ملف التصدير"
                    }, status=500)

                logger.info(f"--- [ExportFileLegacy] File generated, size: {len(final_file)} bytes ---")

                response = HttpResponse(final_file, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = len(final_file)

                logger.info("--- [ExportFileLegacy] Export completed ---")
                return response

            except ImportError as e:
                logger.error(f"--- [ExportFileLegacy] Missing dependency: {e} ---")
                return Response({
                    "error": "مكتبة مفقودة",
                    "message": "مكتبة التصدير غير مثبتة بشكل صحيح"
                }, status=500)

            except Exception as e:
                logger.error(f"--- [ExportFileLegacy] Generation error: {str(e)} ---")
                return Response({
                    "error": "خطأ في توليد الملف",
                    "message": f"حدث خطأ أثناء توليد ملف {format_type}: {str(e)}"
                }, status=500)

        except Exception as e:
            logger.error(f"--- [ExportFileLegacy] Unexpected error: {str(e)} ---")
            return Response({
                "error": "خطأ غير متوقع",
                "message": "حدث خطأ غير متوقع في النظام"
            }, status=500)


@api_view(['GET'])
def export_explanation_file(request, explanation_id, format_type=None):
    """
    تصدير شرح بصيغة PDF أو Markdown
    URL: /api/analysis/ai-explanations/{id}/export-file/{format}/
    أو: /api/analysis/ai-explanations/{id}/export-file/?format={format}
    """
    logger.info(f"--- [ExportAPI] Started for ID: {explanation_id} ---")
    print(f"DEBUG: Export function called with ID: {explanation_id}")
    import sys
    print(f"DEBUG: URL pattern matched for ID: {explanation_id}", file=sys.stderr)

    try:
        # التحقق من صحة الـ ID
        if not explanation_id or not ObjectId.is_valid(explanation_id):
            logger.warning(f"--- [ExportAPI] Invalid ObjectId: {explanation_id} ---")
            return Response({
                "error": "معرف الشرح غير صحيح",
                "message": f"المعرف '{explanation_id}' ليس معرف MongoDB صحيح"
            }, status=400)

        # قراءة format من URL parameter أو query parameter
        format_type = format_type or request.query_params.get('format', 'md')
        format_type = format_type.lower()
        if format_type not in ['pdf', 'md']:
            logger.warning(f"--- [ExportAPI] Unsupported format: {format_type} ---")
            return Response({
                "error": "صيغة الملف غير مدعومة",
                "message": "الصيغ المدعومة هي: pdf, md"
            }, status=400)

        logger.info(f"--- [ExportAPI] Processing ID: {explanation_id}, Format: {format_type} ---")

        # التحقق من الاتصال بقاعدة البيانات
        db = get_mongo_db()
        if db is None:
            logger.error("--- [ExportAPI] Database connection failed ---")
            return Response({
                "error": "خطأ في الاتصال بقاعدة البيانات",
                "message": "تعذر الاتصال بقاعدة بيانات MongoDB"
            }, status=500)

        # البحث عن البيانات
        data = db['ai_explanations'].find_one({"_id": ObjectId(explanation_id)})

        if not data:
            logger.warning(f"--- [ExportAPI] Explanation not found: {explanation_id} ---")
            return Response({
                "error": "الشرح غير موجود",
                "message": f"لم يتم العثور على شرح بالمعرف '{explanation_id}'"
            }, status=404)

        logger.info(f"--- [ExportAPI] Data found, generating {format_type} file ---")

        # التحقق من وجود المحتوى
        if not data.get('content'):
            logger.warning(f"--- [ExportAPI] Empty content for ID: {explanation_id} ---")
            return Response({
                "error": "المحتوى فارغ",
                "message": "لا يحتوي الشرح على أي محتوى للتصدير"
            }, status=404)

        try:
            # اختيار المولد
            if format_type == 'pdf':
                generator = PDFGenerator()
                content_type = 'application/pdf'
                filename = f"technical_report_{explanation_id}.pdf"
            else:
                generator = MarkdownGenerator()
                content_type = 'text/markdown'
                filename = f"technical_report_{explanation_id}.md"

            final_file = generator.generate(data)

            if not final_file:
                logger.error(f"--- [ExportAPI] Generator returned empty file ---")
                return Response({
                    "error": "فشل في توليد الملف",
                    "message": "تعذر توليد ملف التصدير"
                }, status=500)

            logger.info(f"--- [ExportAPI] File generated, size: {len(final_file)} bytes ---")

            response = HttpResponse(final_file, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(final_file)

            logger.info("--- [ExportAPI] Export completed ---")
            return response

        except ImportError as e:
            logger.error(f"--- [ExportAPI] Missing dependency: {e} ---")
            return Response({
                "error": "مكتبة مفقودة",
                "message": "مكتبة التصدير غير مثبتة بشكل صحيح"
            }, status=500)

        except Exception as e:
            logger.error(f"--- [ExportAPI] Generation error: {str(e)} ---")
            return Response({
                "error": "خطأ في توليد الملف",
                "message": f"حدث خطأ أثناء توليد ملف {format_type}: {str(e)}"
            }, status=500)

    except Exception as e:
        logger.error(f"--- [ExportAPI] Unexpected error: {str(e)} ---")
        return Response({
            "error": "خطأ غير متوقع",
            "message": "حدث خطأ غير متوقع في النظام"
        }, status=500)