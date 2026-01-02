# core_ai/ai_engine/orchestrator.py
from ..mongo_utils import get_mongo_db
from .agents import HighLevelAgent, LowLevelAgent, VerifierAgent
from bson import ObjectId
from datetime import datetime
from django.conf import settings

class DocumentationOrchestrator:
    def __init__(self, analysis_id):
        self.analysis_id = analysis_id
        self.db = get_mongo_db()
        # التأكد من استخدام نفس اسم الكولكشن المسجل في settings
        self.collection = self.db[getattr(settings, 'AI_EXPLANATIONS_COLLECTION', 'ai_explanations')]

    def get_or_generate_explanation(self, exp_type):
        # 1. التحقق من وجود الشرح لتوفير الكلفة والوقت (Caching)
        existing = self.collection.find_one({
            "analysis_id": ObjectId(self.analysis_id),
            "explanation_type": exp_type
        })
        if existing:
            return existing['content'], str(existing['_id'])

        # 2. جلب سجل التحليل الأصلي من MongoDB
        analysis_data = self.db[settings.ANALYSIS_RESULTS_COLLECTION].find_one(
            {"_id": ObjectId(self.analysis_id)}
        )
        if not analysis_data:
            raise Exception("Analysis record not found.")

        # استخراج الكود الخام كما هو مطلوب في LowLevelAgent و VerifierAgent
        # لاحظي التسمية code_content لتطابق بارامترات الـ agents
        code_content = analysis_data.get('ast_structure', {}).get('code_content', '')
        
        # 3. تشغيل الوكيل المناسب بناءً على النوع المطلوبة
        if exp_type == 'high':
            print(f"--- DEBUG: [Orchestrator] Generating HIGH LEVEL explanation for analysis_id: {self.analysis_id} ---")
            agent = HighLevelAgent()
            # استخراج بيانات الكلاس (التسميات class_name و associations)
            classes = analysis_data.get('class_diagram_data', {}).get('classes', [])
            if classes:
                class_name = classes[0].get('name', 'Unknown')
                associations = classes[0].get('associations', [])
            else:
                class_name = "General Module"
                associations = "No explicit associations found"

            # استدعاء يطابق توقيع الدالة في agents.py
            raw_content = agent.process(class_name, associations)
            print(f"--- DEBUG: [Orchestrator] High level agent generated content (length: {len(raw_content)}) ---")
        else:
            print(f"--- DEBUG: [Orchestrator] Generating LOW LEVEL explanation for analysis_id: {self.analysis_id} ---")
            agent = LowLevelAgent()
            # استدعاء يطابق توقيع الدالة في agents.py (يمرر code_content)
            raw_content = agent.process(code_content)
            print(f"--- DEBUG: [Orchestrator] Low level agent generated content (length: {len(raw_content)}) ---")

        # 4. مرحلة التدقيق لمنع "هلوسة" الذكاء الاصطناعي
        # يمرر (code, explanation) كما هو في VerifierAgent.verify
        verified_content = VerifierAgent().verify(code=code_content, explanation=raw_content)

        # 5. الحفظ في المونغو لعرضه في الـ Admin لاحقاً
        new_doc = {
            "analysis_id": ObjectId(self.analysis_id),
            "explanation_type": exp_type,
            "content": verified_content,
            "created_at": datetime.utcnow(),
            "code_content": code_content,  # حفظ الكود الأصلي للمراجعة
            "agent_type": "HighLevelAgent" if exp_type == 'high' else "LowLevelAgent"  # تحديد نوع الوكيل
        }

        print(f"--- DEBUG: [Orchestrator] Attempting to save {exp_type} explanation to MongoDB ---")
        print(f"--- DEBUG: [Orchestrator] Document to save: {new_doc.keys()} ---")

        result = self.collection.insert_one(new_doc)

        # طباعة تأكيد الحفظ للتشخيص
        print(f"--- DEBUG: [Orchestrator] ✅ {exp_type.upper()} explanation saved successfully with ID: {result.inserted_id} ---")
        print(f"--- DEBUG: [Orchestrator] Agent type: {new_doc['agent_type']} ---")

        return verified_content, str(result.inserted_id)