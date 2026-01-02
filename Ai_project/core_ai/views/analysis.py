# Ai_project/core_ai/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from core_ai.serializers.analysis import  AnalysisJobSerializer, AnalysisResultSerializer
from core_ai.models.analysis import  AnalysisJob, AnalysisResult, PyObjectId
from core_ai.mongo_utils import get_mongo_db
from django.conf import settings
from bson.objectid import ObjectId
from rest_framework.permissions import AllowAny


class AnalysisJobViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = AnalysisJobSerializer

    def get_collection(self):
        db = get_mongo_db()
        if db is None:
            raise Exception("Could not connect to MongoDB")
        return db[settings.ANALYSIS_JOBS_COLLECTION] # سنعرف هذا في settings.py

    def list(self, request):
        try:
            collection = self.get_collection()
            jobs_data = list(collection.find())
            jobs = [AnalysisJob(**self._prepare_data_for_pydantic(data)) for data in jobs_data]
            serializer = AnalysisJobSerializer(jobs, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        serializer = AnalysisJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            collection = self.get_collection()
            job_instance = AnalysisJob(**serializer.validated_data)
            
            data_to_insert = job_instance.dict(by_alias=True, exclude_unset=True)
            if '_id' in data_to_insert and data_to_insert['_id'] is None:
                del data_to_insert['_id']
            
            result = collection.insert_one(data_to_insert)
            
            job_instance.id = result.inserted_id
            serializer = AnalysisJobSerializer(job_instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            collection = self.get_collection()
            job_data = collection.find_one({"_id": ObjectId(pk)})
            if not job_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            job = AnalysisJob(**self._prepare_data_for_pydantic(job_data))
            serializer = AnalysisJobSerializer(job)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        try:
            collection = self.get_collection()
            job_data = collection.find_one({"_id": ObjectId(pk)})
            if not job_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            
            job_instance = AnalysisJob(**self._prepare_data_for_pydantic(job_data))
            
            serializer = AnalysisJobSerializer(job_instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            updated_data = serializer.validated_data
            
            collection.update_one({"_id": ObjectId(pk)}, {"$set": updated_data})
            
            updated_job_data = collection.find_one({"_id": ObjectId(pk)})
            updated_job_instance = AnalysisJob(**self._prepare_data_for_pydantic(updated_job_data))
            
            return Response(AnalysisJobSerializer(updated_job_instance).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        try:
            collection = self.get_collection()
            result = collection.delete_one({"_id": ObjectId(pk)})
            if result.deleted_count == 0:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def _prepare_data_for_pydantic(self, data):
        if '_id' in data:
            data['id'] = data.pop('_id')
        def convert_object_ids(obj):
            if isinstance(obj, dict):
                return {k: convert_object_ids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_object_ids(elem) for elem in obj]
            elif isinstance(obj, ObjectId):
                return PyObjectId(obj)
            return obj
        return convert_object_ids(data)


class AnalysisResultViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    serializer_class = AnalysisResultSerializer

    @action(detail=True, methods=['get'])
    def class_diagram(self, request, pk=None):
        """الحصول على بيانات class diagram فقط"""
        try:
            collection = self.get_collection()
            result_data = collection.find_one({"_id": ObjectId(pk)})
            if not result_data:
                return Response(status=status.HTTP_404_NOT_FOUND)

            class_diagram_data = result_data.get('class_diagram_data', {"classes": []})
            return Response({"class_diagram_data": class_diagram_data})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_collection(self):
        db = get_mongo_db()
        if db is None:
            raise Exception("Could not connect to MongoDB")
        return db[settings.ANALYSIS_RESULTS_COLLECTION] # سنعرف هذا في settings.py

    def list(self, request):
        try:
            collection = self.get_collection()
            results_data = list(collection.find())
            results = [AnalysisResult(**self._prepare_data_for_pydantic(data)) for data in results_data]
            serializer = AnalysisResultSerializer(results, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            print("--- DEBUG: [AnalysisResultViewSet.list] FATAL EXCEPTION ---")
            print(f"Error: {e}")
            print(traceback.format_exc()) # طباعة الـ traceback الكامل
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        serializer = AnalysisResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            collection = self.get_collection()
            result_instance = AnalysisResult(**serializer.validated_data)
            
            data_to_insert = result_instance.dict(by_alias=True, exclude_unset=True)
            if '_id' in data_to_insert and data_to_insert['_id'] is None:
                del data_to_insert['_id']
            
            result = collection.insert_one(data_to_insert)
            
            result_instance.id = result.inserted_id
            serializer = AnalysisResultSerializer(result_instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def retrieve(self, request, pk=None):
        try:
            collection = self.get_collection()
            result_data = collection.find_one({"_id": ObjectId(pk)})
            if not result_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            result = AnalysisResult(**self._prepare_data_for_pydantic(result_data))
            serializer = AnalysisResultSerializer(result)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def update(self, request, pk=None):
        try:
            collection = self.get_collection()
            result_data = collection.find_one({"_id": ObjectId(pk)})
            if not result_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            
            result_instance = AnalysisResult(**self._prepare_data_for_pydantic(result_data))
            
            serializer = AnalysisResultSerializer(result_instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            updated_data = serializer.validated_data
            
            collection.update_one({"_id": ObjectId(pk)}, {"$set": updated_data})
            
            updated_result_data = collection.find_one({"_id": ObjectId(pk)})
            updated_result_instance = AnalysisResult(**self._prepare_data_for_pydantic(updated_result_data))
            
            return Response(AnalysisResultSerializer(updated_result_instance).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def destroy(self, request, pk=None):
        try:
            collection = self.get_collection()
            result = collection.delete_one({"_id": ObjectId(pk)})
            if result.deleted_count == 0:
                return Response(status=status.HTTP_404_NOT_FOUND)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _prepare_data_for_pydantic(self, data):
        if '_id' in data:
            data['id'] = data.pop('_id')
        def convert_object_ids(obj):
            if isinstance(obj, dict):
                return {k: convert_object_ids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_object_ids(elem) for elem in obj]
            elif isinstance(obj, ObjectId):
                return PyObjectId(obj)
            return obj
        return convert_object_ids(data)
