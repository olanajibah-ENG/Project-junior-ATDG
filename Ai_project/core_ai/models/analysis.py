from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from core_ai.models.codefile import PyObjectId

class AnalysisResult(BaseModel):
    id: Optional[PyObjectId] = Field(default=None,alias="_id")
    code_file_id: PyObjectId # ربط بنموذج CodeFile
    analysis_started_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_completed_at: Optional[datetime] = None
    status: str = "IN_PROGRESS" # IN_PROGRESS, COMPLETED, FAILED
    ast_structure: Optional[Dict[str, Any]] = None
    extracted_features: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    dependency_graph: Optional[Dict[str, Any]] = None
    semantic_analysis_data: Optional[Dict[str, Any]] = None
    class_diagram_data: Optional[Dict[str, Any]] = None

    class Config:
        allow_population_by_field_name = True # تم تغيير هذا
        validate_by_name = True # استخدم هذا بدلاً منه
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AnalysisJob(BaseModel):
    id: Optional[PyObjectId] = Field(default=None,alias="_id")
    code_file_id: PyObjectId # ربط بنموذج CodeFile
    status: str = "CREATED"  # CREATED, STARTED, COMPLETED, FAILED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True # تم تغيير هذا
        validate_by_name = True # استخدم هذا بدلاً منه
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
