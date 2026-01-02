from os import name
from django.shortcuts import get_object_or_404
from core_upm.models import CodeArtifact, Project # الاستيراد من طبقة Models
import uuid
import logging
from core_upm import external_storage
import requests
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
logger = logging.getLogger(name)

AI_CODEFILES_API = settings.AI_SERVICE_URL


class ArtifactRepository:
    # ----------------------------------------------------
    # دوال القراءة والإنشاء في MySQL (تم افتراض وجودها)
    # ----------------------------------------------------
    
    def get_artifact_by_id(self, code_id: str) -> CodeArtifact:
        return get_object_or_404(CodeArtifact, code_id=code_id)
    
    def get_artifacts_by_project(self, project: Project):
        return CodeArtifact.objects.filter(project=project).order_by('-upload_date')
    
    def create_artifact(self, **kwargs) -> CodeArtifact:
        return CodeArtifact.objects.create(**kwargs)
    
    # ----------------------------------------------------
    # الدوال المعدّلة للتواصل مع API (التخزين الخارجي)
    # ----------------------------------------------------

    def save_content_externally(self, content: str, project_id: str , file_name: str,code_language:str) -> str:
        """
        يرسل محتوى الكود إلى خدمة AI ويستقبل مرجع التخزين (ObjectId).
        """
        data = {
            # CodeFileSerializer في AI_Project يحتاج هذه الحقول
            "filename": file_name , # يمكن تخمين اسم مؤقت أو الحصول عليه من Service
            "file_type": code_language,   # يمكن تخمين النوع 
            "content": content,
            "source_project_id": str(project_id) # هذا هو الـ FK للمشروع الأول
        }
        
        try:
            response = requests.post(
                AI_CODEFILES_API, 
                json=data, 
                headers=self._get_auth_headers() ,timeout=10# 👈 إضافة الرأس هنا
            )
            response.raise_for_status()  # يرفع استثناء لأخطاء 4xx/5xx
            
            return response.json()['id']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with AI service during save: {e}")
            error_msg = "Failed to save code content externally."
            if response is not None and response.content:
                 try:
                    details = response.json()
                    error_msg = details.get('detail', error_msg)
                 except requests.exceptions.JSONDecodeError:
                    pass
            raise ValidationError(error_msg)

    def fetch_content_externally(self, storage_reference: str) -> str:
        """
        يجلب محتوى الكود من خدمة AI باستخدام الـ ObjectId.
        """
        url = f"{AI_CODEFILES_API}{storage_reference}/"
        try:
            response = requests.get(
                url, 
                headers=self._get_auth_headers(), # 👈 إضافة الـ headers هنا أيضاً
                timeout=10
            )
            response.raise_for_status()

            # نفترض أن الرد يحتوي على حقل 'content'
            return response.json()['content']            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with AI service during fetch: {e}")
            return "Error retrieving code content."


    @transaction.atomic
    def delete_artifact(self, artifact: CodeArtifact) :
        """
        يحذف Artifact من MySQL ويحذف المحتوى من MongoDB.
        """
        storage_reference = artifact.storage_reference
        url = f"{AI_CODEFILES_API}{storage_reference}/"
        try:
            # 🛑 التعديل الثالث: إضافة الـ headers
            response = requests.delete(
                url,
                headers=self._get_auth_headers(), # 👈 إضافة الـ headers هنا أيضاً
                timeout=10
            )
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete external content {storage_reference}: {e}")
            # يمكن هنا اتخاذ قرار إما برفع استثناء (لإلغاء عملية الحذف بالكامل) أو تسجيل خطأ والاستمرار.
            # في هذه الحالة، سنستمر مع تسجيل خطأ، لأن سجل MySQL قد حُذف بالفعل.
            raise

        # 2. حذف السجل من قاعدة البيانات المحلية (MySQL)
        artifact.delete()

    def _get_auth_headers(self):
        # افترض أن مفتاح API الخاص بالخدمة مخزن أيضاً في إعدادات UPM
        service_key = settings.AI_SERVICE_KEY 
        clean_host_header = 'ai_web' 
        
        headers = {
            'X-API-KEY': service_key,
            # 💡 إضافة Host Header اليدوي
            'Host': clean_host_header 
        }
        
        return headers        