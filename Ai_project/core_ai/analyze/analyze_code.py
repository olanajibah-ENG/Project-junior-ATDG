import traceback
from core_ai.language_processors.python_processor import PythonProcessor  
from core_ai.language_processors.java_processor import JavaProcessor
from .project_analyzer import ProjectAnalyzer
from core_ai.models import CodeFile, AnalysisResult, AnalysisJob, PyObjectId
from core_ai.mongo_utils import get_mongo_db
from django.conf import settings
from datetime import datetime
# Optional Celery import
try:
    from celery import shared_task
except ImportError:
    # Celery not installed, create dummy decorator
    def shared_task(func):
        return func
from bson.objectid import ObjectId

@shared_task
def analyze_code_file_task2(code_file_id_str):
    db = get_mongo_db()
    if  db is None:
        print("Failed to connect to MongoDB in Celery task v2 db is none.")
        return

    code_files_collection = db[settings.CODE_FILES_COLLECTION]
    analysis_jobs_collection = db[settings.ANALYSIS_JOBS_COLLECTION]
    analysis_results_collection = db[settings.ANALYSIS_RESULTS_COLLECTION]

    code_file_id=None
    job_id=None
    code_file=None
    try:
        code_file_id_obj = ObjectId(code_file_id_str)
        
        # 1. استرجاع CodeFile
        code_file_data = code_files_collection.find_one({"_id": code_file_id_obj})
        if not code_file_data:
         logger.warning(f"CodeFile with ID {code_file_id_str} not found in DB using ObjectId. CRITICAL! (Check Mongo connection/ID casting)")        
         return

        # تحويل MongoDB ObjectId إلى Pydantic PyObjectId
        if '_id' in code_file_data:
            code_file_data['id'] = code_file_data.pop('_id')
        code_file = CodeFile(**code_file_data)

        # 2. إنشاء AnalysisJob
        job_data = {
            "code_file_id": code_file_id_obj,
            "status": "STARTED",
            "created_at": datetime.utcnow(),
            "started_at": datetime.utcnow()
        }
        job_result = analysis_jobs_collection.insert_one(job_data)
        job_id = job_result.inserted_id
 
        # 3. تحديث حالة CodeFile
        code_files_collection.update_one(
            {"_id": code_file_id_obj},
            {"$set": {"analysis_status": "IN_PROGRESS"}}
        )

        # 4. اختيار المعالج وتحليل الكود
        processor_map = {
            "python": PythonProcessor(),
            "java": JavaProcessor(), # إذا كان لديك معالج Java
            # أضف المزيد من المعالجات هنا
        }
        processor = processor_map.get(code_file.file_type.lower())

        if  processor is None:
            raise ValueError(f"No processor found for file type: {code_file.file_type}")
    
        analyzer = ProjectAnalyzer(processor)
        
        # تنفيذ خطوات التحليل
        analysis_data = analyzer.analyze_code(code_file.content)
        ast=analysis_data.get("ast_structure",{}) 
        if "ast_tree" in ast :
             del ast["ast_tree"]
        features = analysis_data.get("features_extracted")
        dependencies_list = analysis_data.get("dependencies")
        semantic_data = analysis_data.get("semantic_analysis_output")
        class_diagram_data = analysis_data.get("class_diagram_data")
        dependency_graph_dict=analysis_data.get("dependency_graph")
     
        print(f"DEBUG: [CELERY-SAVE] dependencies type: {type(dependencies_list)}")
        print(f"DEBUG: [CELERY-SAVE] dependency_graph type: {type(dependency_graph_dict)}")
        # 5. حفظ نتائج التحليل

        result_data = {
            "code_file_id": code_file_id_obj,
            "analysis_started_at": job_data["started_at"],
            "analysis_completed_at": datetime.utcnow(),
            "status": "COMPLETED",
            "ast_structure": ast,
            "extracted_features": features,
            "dependencies": dependencies_list,
            "dependency_graph": dependency_graph_dict,
            "semantic_analysis_data": semantic_data,
            "class_diagram_data": class_diagram_data
        }
        analysis_results_collection.insert_one(result_data)

        # 6. تحديث حالة CodeFile و AnalysisJob
        code_files_collection.update_one(
            {"_id": code_file_id_obj},
            {"$set": {"analysis_status": "COMPLETED"}}
        )
        analysis_jobs_collection.update_one(
            {"_id": job_id},
            {"$set": {"status": "COMPLETED", "completed_at": datetime.utcnow()}}
        )

        print(f"Analysis for CodeFile {code_file_id_str} completed successfully.")

    except Exception as e:
        error_message = f"Analysis failed for CodeFile {code_file_id_str}: {e}"
        print("---FATAL ANALYSIS ERROR TRACEBACK---")
        print(error_message)
        print(traceback.format_exc())
        print("--------------------------------------------")
        if code_file is not None:
            code_files_collection.update_one(
                {"_id": code_file.id},
                {"$set": {"analysis_status": "FAILED"}}
            )
        if job_id is not None:
            analysis_jobs_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "FAILED", "completed_at": datetime.utcnow(), "error_message": error_message}}
            )
