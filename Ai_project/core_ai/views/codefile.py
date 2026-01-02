# Ai_project/core_ai/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from core_ai.serializers.codefile import CodeFileSerializer
from core_ai.models.codefile import CodeFile, PyObjectId
from core_ai.mongo_utils import get_mongo_db
from core_ai.analyze.analyze_code import analyze_code_file_task2
from django.conf import settings
from bson.objectid import ObjectId
from rest_framework.permissions import AllowAny

class CodeFileViewSet(viewsets.ViewSet):
    permission_classes=[AllowAny]
    serializer_class = CodeFileSerializer

    def get_collection(self):
        db = get_mongo_db()
        if  db is None:
            raise Exception("Failed to establish connection with MongoDB.")
        return db[settings.CODE_FILES_COLLECTION] # سنعرف هذا في settings.py

    def list(self, request):
        try:
            collection = self.get_collection()
            code_files_data = list(collection.find())
            # تحويل ObjectId إلى PyObjectId لتمريره إلى Pydantic model
            code_files = [CodeFile(**self._prepare_data_for_pydantic(data)) for data in code_files_data]
            serializer = CodeFileSerializer(code_files, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        print("--- DEBUG: [CF-CREATE] Starting CodeFile creation ---")

        # سيعمل Serializer الآن على قراءة البيانات سواء من JSON (لحقل content) أو form-data (لحقل uploaded_file)
        serializer = CodeFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 🚨 المنطق الجديد للتعامل مع الملف المرفوع 🚨
        validated_data = serializer.validated_data.copy()

        if 'uploaded_file' in validated_data and validated_data['uploaded_file']:
            uploaded_file = validated_data.pop('uploaded_file') # استخرج كائن الملف

            # قراءة محتوى الملف وتحويله إلى سلسلة نصية UTF-8
            try:
                file_content = uploaded_file.read().decode('utf-8')
                validated_data['content'] = file_content
                print(f"--- DEBUG: [CF-CREATE] File content loaded, size: {len(file_content)} chars ---")
            except Exception as e:
                print(f"--- DEBUG: [CF-CREATE] Failed to read file content: {e} ---")
                return Response({"error": f"Failed to read file content: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # إذا لم يكن هناك uploaded_file، فإن validated_data['content'] سيكون قد تم ملؤه من JSON مباشرة

        try:
            print("--- DEBUG: [CF-CREATE] Attempting to get MongoDB collection ---")
            collection = self.get_collection()

            if collection is None:
                 print("--- DEBUG: [CF-CREATE] MongoDB collection is None! ---")
                 raise Exception("MongoDB collection object is missing.")

            # تهيئة كائن CodeFile من البيانات المتحقق منها (التي تحتوي الآن على content كـ نص)
            code_file_instance = CodeFile(**validated_data)
            
            # تحويل PyObjectId إلى ObjectId لـ MongoDB
            # وإزالة حقل id لأنه سيتولد تلقائياً بواسطة MongoDB
            data_to_insert = code_file_instance.dict(by_alias=True, exclude_unset=True)
            if '_id' in data_to_insert and data_to_insert['_id'] is None:
                del data_to_insert['_id']
            
            print(f"--- DEBUG: [CF-CREATE] Data ready for insert: {data_to_insert} ---")
            result = collection.insert_one(data_to_insert)
            print(f"--- DEBUG: [CF-CREATE] MongoDB insert successful. ID: {result.inserted_id} ---")
            # إعادة بناء الكائن مع الـ ID الذي تم توليده
            code_file_instance.id = result.inserted_id
            serializer = CodeFileSerializer(code_file_instance) # إعادة تسلسل الكائن الجديد
            
            print("--- DEBUG: [CF-CREATE] Launching Celery task ---")
            # إطلاق مهمة Celery للتحليل في الخلفية
            analyze_code_file_task2.delay(str(result.inserted_id)) # تمرير الـ ID كسلسلة
            
            print("--- DEBUG: [CF-CREATE] Returning 201 response ---")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
                # 🚨 طباعة الخطأ كاملاً هنا لتشخيص الـ 500
            import traceback
            print(f"--- DEBUG: [CF-CREATE] FATAL EXCEPTION: {e}")
            print(traceback.format_exc()) # طباعة الـ traceback
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            collection = self.get_collection()
            code_file_data = collection.find_one({"_id": ObjectId(pk)})
            if not code_file_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            code_file = CodeFile(**self._prepare_data_for_pydantic(code_file_data))
            serializer = CodeFileSerializer(code_file)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        try:
            collection = self.get_collection()
            code_file_data = collection.find_one({"_id": ObjectId(pk)})
            if not code_file_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            
            code_file_instance = CodeFile(**self._prepare_data_for_pydantic(code_file_data))
            
            serializer = CodeFileSerializer(code_file_instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            updated_data = serializer.validated_data
            
            # تحديث MongoDB
            collection.update_one({"_id": ObjectId(pk)}, {"$set": updated_data})
            
            # استرجاع الكائن المحدث من DB للتأكد
            updated_code_file_data = collection.find_one({"_id": ObjectId(pk)})
            updated_code_file_instance = CodeFile(**self._prepare_data_for_pydantic(updated_code_file_data))
            
            return Response(CodeFileSerializer(updated_code_file_instance).data)
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

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        try:
            collection = self.get_collection()
            code_file_data = collection.find_one({"_id": ObjectId(pk)})
            if not code_file_data:
                return Response(status=status.HTTP_404_NOT_FOUND)
            
            # تحديث حالة ملف الكود إلى IN_PROGRESS
            collection.update_one({"_id": ObjectId(pk)}, {"$set": {"analysis_status": "IN_PROGRESS"}})

            # إطلاق مهمة Celery للتحليل
            analyze_code_file_task2.delay(pk)
            return Response({"message": f"Analysis for CodeFile {pk} started."}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _prepare_data_for_pydantic(self, data):
        """
        Helper to convert MongoDB _id to 'id' for Pydantic models.
        Also converts ObjectId values within the document.
        """
        if '_id' in data:
            data['id'] = data.pop('_id')
        
        # Recursively convert ObjectId in nested dictionaries/lists
        def convert_object_ids(obj):
            if isinstance(obj, dict):
                return {k: convert_object_ids(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_object_ids(elem) for elem in obj]
            elif isinstance(obj, ObjectId):
                return PyObjectId(obj)
            return obj
        
        return convert_object_ids(data)


