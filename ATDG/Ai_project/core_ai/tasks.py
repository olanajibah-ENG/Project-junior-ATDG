import logging
from celery import shared_task
from core_ai.mongo_utils import get_mongo_db
from core_ai.ai_engine.orchestrator import DocumentationOrchestrator
from core_ai.repository.ai_task import AITask
from core_ai.notification_utils import NotificationClient
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_ai_explanation_task(self, analysis_id, exp_type, user_email=None):
    """
    Celery task لتوليد شرح AI في الخلفية

    Args:
        analysis_id (str): معرف تحليل الكود
        exp_type (str): نوع الشرح المطلوب

    Returns:
        dict: نتيجة التوليد
    """
    task_record = AITask(
        task_id=self.request.id,
        analysis_id=analysis_id,
        exp_type=exp_type,
        status='processing'
    )

    try:
        task_record.save()
        logger.info(f"--- [Celery Task] Starting AI explanation generation for analysis_id: {analysis_id}, type: {exp_type} ---")

        if not ObjectId.is_valid(analysis_id):
            raise ValueError(f"Invalid analysis_id format: {analysis_id}")

        orchestrator = DocumentationOrchestrator(analysis_id=analysis_id)

        content, explanation_id = orchestrator.get_or_generate_explanation(exp_type)

        result = {
            "status": "completed",
            "explanation_id": str(explanation_id),
            "type": exp_type,
            "content": content,
            "analysis_id": analysis_id
        }

        task_record.update_status('completed', result=result)

        logger.info(f"--- [Celery Task] Successfully generated explanation for analysis_id: {analysis_id} ---")

        if user_email:
            try:
                NotificationClient.send_custom_notification(
                    user_email=user_email,
                    title="تم إكمال تحليل الكود بنجاح",
                    message=f"تم توليد شرح {exp_type} لتحليل الكود بنجاح. يمكنك الآن عرض النتائج.",
                    notification_type="CODE_ANALYZED",
                    user_name=""
                )
            except Exception as notification_error:
                logger.warning(f"Failed to send success notification: {str(notification_error)}")

        return result

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"--- [Celery Task] Error for analysis_id: {analysis_id}, type: {exp_type} ---")
        logger.error(f"--- [Celery Task] Error message: {error_msg} ---")
        logger.error(f"--- [Celery Task] Traceback: {error_traceback} ---")

        try:
            task_record.update_status('failed', error=error_msg)
        except Exception as db_error:
            logger.error(f"--- [Celery Task] Failed to update task status: {str(db_error)} ---")

        if user_email:
            try:
                NotificationClient.send_system_alert(
                    user_email=user_email,
                    alert_type="error",
                    message=f"فشل في تحليل الكود. نوع التحليل: {exp_type}. الخطأ: {error_msg}",
                    user_name=""
                )
            except Exception as notification_error:
                logger.warning(f"Failed to send error notification: {str(notification_error)}")

        raise Exception(f"AI explanation generation failed: {error_msg}")
