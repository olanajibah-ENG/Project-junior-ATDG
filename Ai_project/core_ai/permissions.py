# Ai_project/core_ai/permissions.py
from rest_framework.permissions import BasePermission
from django.conf import settings

class IsServiceToService(BasePermission):
    """
    Custom permission to allow access only if a specific secret API key is provided in the header.
    """
    def has_permission(self, request, view):
        # تحقق من الرأس (Header) المخصص
        # نستخدم رأساً شائعاً مثل X-API-Key
        api_key = request.headers.get('X-API-KEY')
        # يجب تعريف SERVICE_API_KEY في settings.py للمشروع AI
        expected_key = getattr(settings, 'SERVICE_API_KEY', None)

        # السماح بالوصول فقط إذا كان المفتاح متطابقاً وتم توفيره
        return bool(api_key and api_key == expected_key)