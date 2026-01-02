from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from core_ai.models.codefile import PyObjectId

class AIExplanation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    analysis_id: PyObjectId  # ربط بـ AnalysisResult
    explanation_type: str    # 'high_level' أو 'low_level'
    content: str             # نص الشرح الناتج من AI
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}