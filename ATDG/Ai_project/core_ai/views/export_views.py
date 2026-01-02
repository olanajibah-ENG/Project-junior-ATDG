import logging
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from bson.objectid import ObjectId
from core_ai.mongo_utils import get_mongo_db
from core_ai.ai_engine.doc.markdown import MarkdownGenerator
from core_ai.ai_engine.doc.pdf import PDFGenerator
from core_ai.notification_utils import NotificationClient
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

logger = logging.getLogger(__name__)

try:
    from core_ai.tasks import generate_ai_explanation_task
    CELERY_AVAILABLE = True
except Exception as e:
    logger.warning(f"Celery not available: {e}")
    CELERY_AVAILABLE = False
    generate_ai_explanation_task = None


def handle_export_with_auto_generation(analysis_id, explanation_type, format_type, image_url=None, user_email=None):
    """
    نقطة الدخول الموحدة لتصدير التوثيق مع التوليد التلقائي
    تدعم جميع أنواع التصدير والتحقق التلقائي من وجود الشرح
    """
    logger.info(f"--- [ExportHandler] Starting export for analysis_id: {analysis_id}, type: {explanation_type} ---")
    
    try:
        db = get_mongo_db()
        if db is None:
            logger.error("--- [ExportHandler] Database connection failed ---")
            return JsonResponse({
                "error": "Database connection error",
                "message": "Failed to connect to MongoDB database"
            }, status=500)

        collection_name = getattr(settings, 'AI_EXPLANATIONS_COLLECTION', 'ai_explanations')
        
        try:
            if ObjectId.is_valid(analysis_id):
                analysis_obj_id = ObjectId(analysis_id)
            else:
                analysis_obj_id = analysis_id
        except:
            analysis_obj_id = analysis_id

        search_criteria_new = {
            "analysis_id": analysis_obj_id,
            "exp_type": explanation_type
        }
        data = db[collection_name].find_one(search_criteria_new)

        if data is not None:
            if not isinstance(data, dict):
                logger.warning(f"--- [ExportHandler] Invalid data type from new search: {type(data)} ---")
                data = None
            else:
                if '_id' in data and hasattr(data['_id'], '__class__') and 'ObjectId' in str(data['_id'].__class__):
                    data['_id'] = str(data['_id'])
                for key, value in data.items():
                    if hasattr(value, '__class__') and 'ObjectId' in str(value.__class__):
                        data[key] = str(value)

        if not data:
            search_criteria_old = {
                "analysis_id": analysis_obj_id,
                "explanation_type": explanation_type
            }
            data = db[collection_name].find_one(search_criteria_old)

            if data is not None:
                if not isinstance(data, dict):
                    logger.warning(f"--- [ExportHandler] Invalid data type from old search: {type(data)} ---")
                    data = None
                else:
                    if '_id' in data and hasattr(data['_id'], '__class__') and 'ObjectId' in str(data['_id'].__class__):
                        data['_id'] = str(data['_id'])
                    for key, value in data.items():
                        if hasattr(value, '__class__') and 'ObjectId' in str(value.__class__):
                            data[key] = str(value)

        logger.info(f"--- [ExportHandler] Search result: {data is not None} ---")
        if data:
            logger.info(f"--- [ExportHandler] Data type: {type(data)} ---")
            if isinstance(data, dict):
                logger.info(f"--- [ExportHandler] Data _id type: {type(data.get('_id'))} ---")
            else:
                logger.warning(f"--- [ExportHandler] Data is not a dict, it's: {type(data)} ---")

        if not data:
            logger.info(f"--- [ExportHandler] Explanation not found in main collection, checking task status ---")
            
            tasks_collection = getattr(settings, 'AI_TASKS_COLLECTION', 'ai_tasks')
            task_data = db[tasks_collection].find_one({
                "analysis_id": analysis_id,
                "exp_type": explanation_type,
                "status": "completed"
            })
            
            if task_data and isinstance(task_data, dict) and task_data.get('result', {}).get('content'):
                logger.info(f"--- [ExportHandler] Found completed task with content ---")
                data = {
                    '_id': task_data.get('result', {}).get('explanation_id', 'temp_id'),
                    'content': task_data['result']['content'],
                    'exp_type': explanation_type,
                    'analysis_id': analysis_id,
                    'created_at': task_data.get('created_at')
                }
            else:
                logger.info(f"--- [ExportHandler] No completed task found either, generating new explanation ---")
                
                analysis_collection = getattr(settings, 'ANALYSIS_RESULTS_COLLECTION', 'analysis_results')
                analysis_data = db[analysis_collection].find_one({"_id": ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id})
                
                if not analysis_data:
                    return JsonResponse({
                        "error": "Analysis not found",
                        "message": f"No analysis found with ID '{analysis_id}'. Code must be analyzed first.",
                        "suggestion": "Analyze the code first then try again"
                    }, status=404)
                
                if not CELERY_AVAILABLE or generate_ai_explanation_task is None:
                    return JsonResponse({
                        "error": "Generation system unavailable",
                        "message": "Celery system is currently unavailable. Cannot generate new explanation.",
                        "suggestion": "Make sure Celery and Redis are running"
                    }, status=503)
                
                try:
                    task = generate_ai_explanation_task.delay(analysis_id, explanation_type)
                    
                    return JsonResponse({
                        "status": "generating",
                        "message": "Generating requested explanation. Please wait...",
                        "task_id": task.id,
                        "analysis_id": analysis_id,
                        "explanation_type": explanation_type,
                        "estimated_time": "30-60 ثانية"
                    }, status=202)  # 202 Accepted
                except Exception as e:
                    logger.error(f"--- [ExportHandler] Celery task creation failed: {e} ---")
                    return JsonResponse({
                        "error": "Failed to start generation",
                        "message": f"An error occurred while starting explanation generation: {str(e)}",
                        "suggestion": "Make sure Celery and Redis are running"
                    }, status=503)

        if not data.get('content'):
            return JsonResponse({
                "error": "Empty content",
                "message": "Explanation exists but content is empty"
            }, status=404)

        if not isinstance(data, dict):
            logger.error(f"--- [ExportHandler] Invalid data type returned: {type(data)} ---")
            return JsonResponse({
                "error": "Invalid data",
                "message": f"Explanation found but data is invalid. Data type: {type(data)}"
            }, status=500)

        if not data.get('content'):
            logger.error(f"--- [ExportHandler] Missing content in data: {data.keys() if hasattr(data, 'keys') else 'No keys'} ---")
            return JsonResponse({
                "error": "Empty content",
                "message": "Explanation exists but content is empty"
            }, status=404)

        logger.info(f"--- [ExportHandler] Found explanation data: {type(data)} ---")
        logger.info(f"--- [ExportHandler] Data keys: {list(data.keys())} ---")

        if image_url:
            data['image_url'] = image_url

        try:
            logger.info(f"--- [ExportHandler] About to generate file with data type: {type(data)} ---")
            logger.info(f"--- [ExportHandler] Data content preview: {str(data)[:200]}... ---")

            content_value = data.get('content', '')
            logger.info(f"--- [ExportHandler] Content value type: {type(content_value)}, length: {len(str(content_value)) if content_value else 0} ---")

            if format_type == 'pdf':
                logger.info("--- [ExportHandler] Creating PDF generator ---")
                generator = PDFGenerator()
                content_type = 'application/pdf'
                filename = f"technical_report_{explanation_type}_{analysis_id[:8]}.pdf"
            else:
                logger.info("--- [ExportHandler] Creating Markdown generator ---")
                generator = MarkdownGenerator()
                content_type = 'text/markdown'
                filename = f"technical_report_{explanation_type}_{analysis_id[:8]}.md"

            logger.info(f"--- [ExportHandler] Calling generator.generate() with content type: {type(content_value)} ---")
            file_content = generator.generate(data)

            if not file_content:
                return JsonResponse({
                    "error": "File generation failed",
                    "message": f"Failed to generate {format_type} file"
                }, status=500)

            logger.info(f"--- [ExportHandler] File generated successfully, size: {len(file_content)} bytes ---")

            try:
                from datetime import datetime
                
                if isinstance(data, dict):
                    explanation_id = data.get('_id', 'unknown')
                    if hasattr(explanation_id, '__class__') and 'ObjectId' in str(explanation_id.__class__):
                        explanation_id = str(explanation_id)
                else:
                    explanation_id = 'unknown'
                
                try:
                    if ObjectId.is_valid(analysis_id):
                        analysis_id_obj = ObjectId(analysis_id)
                    else:
                        analysis_id_obj = analysis_id
                except:
                    analysis_id_obj = analysis_id
                
                file_record = {
                    'explanation_id': explanation_id,
                    'analysis_id': analysis_id_obj,
                    'filename': filename,
                    'file_type': 'pdf' if format_type == 'pdf' else 'markdown',
                    'file_content': file_content,
                    'file_size': len(file_content),
                    'created_at': datetime.utcnow(),
                    'downloaded_count': 1
                }
                result = db[settings.GENERATED_FILES_COLLECTION].insert_one(file_record)
                logger.info(f"--- [ExportHandler] File saved to database with ID: {result.inserted_id} ---")
            except Exception as e:
                logger.error(f"--- [ExportHandler] Error saving file to database: {e} ---")

            if user_email:
                try:
                    NotificationClient.send_documentation_notification(
                        user_email=user_email,
                        file_name=filename,
                        file_type=format_type,
                        project_name="تحليل الكود",
                        user_name=""
                    )
                except Exception as notification_error:
                    logger.warning(f"Failed to send export notification: {str(notification_error)}")

            response = HttpResponse(file_content, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_content)

            return response

        except Exception as e:
            logger.error(f"--- [ExportHandler] Generation error: {str(e)} ---")

            error_msg = str(e)
            if "cairo" in error_msg.lower() or "pdf" in error_msg.lower() and "not supported" in error_msg.lower():
                return JsonResponse({
                    "error": "PDF not supported",
                    "message": "PDF file generation is currently unavailable due to missing Cairo library. Please use Markdown format instead.",
                    "suggestion": "Use format=md in the link instead of format=pdf"
                }, status=503)

            return JsonResponse({
                "error": "File generation error",
                "message": f"An error occurred during file generation: {str(e)}"
            }, status=500)

    except Exception as e:
        logger.error(f"--- [ExportHandler] Error: {str(e)} ---")
        return JsonResponse({
            "error": "System error",
            "message": f"An error occurred while processing the request: {str(e)}"
        }, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def export_doc(request, analysis_id):
    """
    نقطة الدخول الموحدة لتصدير التوثيق
    
    URL: /api/export/<str:analysis_id>/
    
    Query Parameters أو POST Body:
    - format: pdf|markdown (افتراضي: pdf)
    - type: high|low|detailed (افتراضي: detailed) 
    - image_url: رابط الصورة (اختياري)
    
    يرجع الملف مباشرة للتحميل
    """
    logger.info(f"--- [ExportDoc] Export request for analysis_id: {analysis_id} ---")
    
    try:
        if request.method == 'POST':
            try:
                if request.content_type == 'application/json':
                    request_data = json.loads(request.body)
                else:
                    request_data = request.POST.dict()
            except json.JSONDecodeError:
                request_data = {}
        else:
            request_data = request.GET.dict()

        format_type = request_data.get('format', 'pdf').lower().strip()
        explanation_type = request_data.get('type', 'detailed').lower().strip()
        image_url = request_data.get('image_url', '').strip()
        user_email = request_data.get('user_email', '').strip()

        if format_type not in ['pdf', 'markdown', 'md']:
            return JsonResponse({
                "error": "Unsupported format",
                "message": "Supported formats: pdf, markdown, md"
            }, status=400)

        if explanation_type not in ['high', 'low', 'detailed']:
            return JsonResponse({
                "error": "Unsupported explanation type",
                "message": "Supported types: high, low, detailed"
            }, status=400)

        if format_type in ['markdown', 'md']:
            format_type = 'md'

        if explanation_type == 'high':
            db_explanation_type = 'high_level'
        elif explanation_type == 'low':
            db_explanation_type = 'low_level'
        elif explanation_type == 'detailed':
            db_explanation_type = 'low_level'  # detailed يعني low_level
        else:
            db_explanation_type = explanation_type

        logger.info(f"--- [ExportDoc] Parameters - Format: {format_type}, Type: {explanation_type} -> DB Type: {db_explanation_type} ---")

        return handle_export_with_auto_generation(analysis_id, db_explanation_type, format_type, image_url, user_email)

    except Exception as e:
        logger.error(f"--- [ExportDoc] Error: {str(e)} ---")
        return JsonResponse({
            "error": "System error",
            "message": f"An error occurred while processing the request: {str(e)}"
        }, status=500)


def list_generated_files_view(request):
    """
    جلب قائمة بكل ملفات التوثيق التي تم توليدها وتخزينها
    
    URL: /api/generated-files/
    """
    try:
        db = get_mongo_db()
        if db is None:
            return JsonResponse({
                "error": "Database connection error"
            }, status=500)

        files = list(db[settings.GENERATED_FILES_COLLECTION].find(
            {}, 
            {"file_content": 0}
        ).sort("created_at", -1))

        for f in files:
            f['_id'] = str(f['_id'])
            if 'explanation_id' in f: 
                f['explanation_id'] = str(f['explanation_id'])
            if 'analysis_id' in f:
                f['analysis_id'] = str(f['analysis_id'])

        return JsonResponse({"files": files}, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def download_generated_file(request, file_id):
    """
    تحميل ملف مولد من قاعدة البيانات
    URL: /api/download-generated-file/<str:file_id>/
    """
    logger.info(f"--- [DownloadGeneratedFile] Request for file ID: {file_id} ---")

    try:
        db = get_mongo_db()
        if db is None:
            logger.error("--- [DownloadGeneratedFile] Database connection failed ---")
            return JsonResponse({
                "error": "Database connection error",
                "message": "Failed to connect to MongoDB database"
            }, status=500)

        try:
            if ObjectId.is_valid(file_id):
                file_data = db[settings.GENERATED_FILES_COLLECTION].find_one({"_id": ObjectId(file_id)})
            else:
                file_data = db[settings.GENERATED_FILES_COLLECTION].find_one({"_id": file_id})
        except:
            file_data = db[settings.GENERATED_FILES_COLLECTION].find_one({"_id": file_id})

        if not file_data:
            logger.warning(f"--- [DownloadGeneratedFile] File not found: {file_id} ---")
            return JsonResponse({
                "error": "File not found",
                "message": f"File with ID '{file_id}' not found"
            }, status=404)

        try:
            db[settings.GENERATED_FILES_COLLECTION].update_one(
                {"_id": file_data["_id"]},
                {"$inc": {"downloaded_count": 1}}
            )
        except Exception as e:
            logger.warning(f"--- [DownloadGeneratedFile] Failed to update download count: {e} ---")

        filename = file_data.get('filename', f'generated_file_{file_id}')
        file_content = file_data.get('file_content', b'')
        file_type = file_data.get('file_type', 'unknown')

        if file_type == 'pdf':
            content_type = 'application/pdf'
        elif file_type == 'markdown':
            content_type = 'text/markdown'
        else:
            content_type = 'application/octet-stream'

        logger.info(f"--- [DownloadGeneratedFile] Serving file: {filename}, size: {len(file_content)} bytes ---")

        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_content)

        return response

    except Exception as e:
        logger.error(f"--- [DownloadGeneratedFile] Error: {str(e)} ---")
        return JsonResponse({
            "error": "خطأ في النظام",
            "message": f"حدث خطأ أثناء تحميل الملف: {str(e)}"
        }, status=500)