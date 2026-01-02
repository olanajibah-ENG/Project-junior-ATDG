"""
نموذج مهام الذكاء الاصطناعي (AI Tasks)
يحتوي على:
- Instance Methods: للعمليات على كائن واحد (save, update_status)
- Class Methods: للاستعلامات العامة (get_by_task_id, get_user_tasks)
"""

from datetime import datetime
from core_ai.mongo_utils import get_mongo_db
from bson.objectid import ObjectId


class AITask:
    """
    نموذج لإدارة مهام الذكاء الاصطناعي في MongoDB
    مسؤول عن: حفظ المهام، تحديث الحالة، البحث في قاعدة البيانات
    """
    collection_name = 'ai_tasks'

    def __init__(self, task_id, analysis_id, exp_type, status='pending', created_at=None):
        self.task_id = task_id
        self.analysis_id = analysis_id
        self.exp_type = exp_type
        self.status = status  # pending, processing, completed, failed
        self.created_at = created_at or datetime.utcnow()
        self.completed_at = None
        self.result = None
        self.error = None


    def save(self):
        """حفظ المهمة الجديدة في قاعدة البيانات"""
        db = get_mongo_db()
        if db is None:
            raise Exception("تعذر الاتصال بقاعدة البيانات")

        data = {
            "task_id": self.task_id,
            "analysis_id": self.analysis_id,
            "exp_type": self.exp_type,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }

        result = db[self.collection_name].insert_one(data)
        return result.inserted_id

    def update_status(self, status, result=None, error=None):
        """تحديث حالة المهمة الموجودة"""
        db = get_mongo_db()
        if db is None:
            raise Exception("تعذر الاتصال بقاعدة البيانات")

        update_data = {"status": status}

        if result is not None:
            update_data["result"] = result
            update_data["completed_at"] = datetime.utcnow()

        if error is not None:
            update_data["error"] = error
            update_data["completed_at"] = datetime.utcnow()

        db[self.collection_name].update_one(
            {"task_id": self.task_id},
            {"$set": update_data}
        )


    @classmethod
    def get_by_task_id(cls, task_id):
        """
        البحث عن مهمة واحدة بواسطة task_id
        مثال: task = AITask.get_by_task_id("abc-123")
        """
        db = get_mongo_db()
        if db is None:
            return None

        data = db[cls.collection_name].find_one({"task_id": task_id})
        if data:
            task = cls(
                task_id=data["task_id"],
                analysis_id=data["analysis_id"],
                exp_type=data["exp_type"],
                status=data["status"],
                created_at=data["created_at"]
            )
            task.completed_at = data.get("completed_at")
            task.result = data.get("result")
            task.error = data.get("error")
            return task
        return None

    @classmethod
    def get_user_tasks(cls, analysis_id=None, limit=50):
        """
        الحصول على قائمة المهام مع فلترة اختيارية
        مثال: tasks = AITask.get_user_tasks("analysis-123")
        """
        db = get_mongo_db()
        if db is None:
            return []

        query = {}
        if analysis_id:
            query["analysis_id"] = analysis_id

        tasks_data = list(
            db[cls.collection_name]
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
        )

        task_objects = []
        for data in tasks_data:
            task = cls(
                task_id=data["task_id"],
                analysis_id=data["analysis_id"],
                exp_type=data["exp_type"],
                status=data["status"],
                created_at=data["created_at"]
            )
            task.completed_at = data.get("completed_at")
            task.result = data.get("result")
            task.error = data.get("error")
            task_objects.append(task)

        return task_objects
