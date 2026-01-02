# Ai_project/core_ai/models.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

# Handle both pydantic v1 and v2
try:
    from pydantic.json import ENCODERS_BY_TYPE
except ImportError:
    # pydantic v2 compatibility
    ENCODERS_BY_TYPE = {}

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value,values,config,field): # عودة إلى توقيع أبسط، حيث أن info لم تعد ضرورية هنا
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)
        
    @classmethod
    def modify_schema(cls, field_schema):
        field_schema.update(type="string")

ENCODERS_BY_TYPE[PyObjectId]=str

# الآن قم بتحديث كل نماذج BaseModel لتغيير `allow_population_by_field_name`
class CodeFile(BaseModel):
    id: Optional[PyObjectId] = Field(default=None,alias="_id")
    filename: str
    file_type: str  # e.g., 'python', 'java', 'javascript'
    content: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    source_project_id: Optional[str] = None  # لربطها بمشروع UPM
    analysis_status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED

    class Config:
        allow_population_by_field_name = True # تم تغيير هذا
        validate_by_name = True # استخدم هذا بدلاً منه
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

