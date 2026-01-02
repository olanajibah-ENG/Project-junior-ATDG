# core_ai/ai_engine/agents.py
from .llm_client import GeminiClient

class BaseAgent:
    """Base class for all AI Agents"""
    def ask_ai(self, system_prompt, user_prompt):
        return GeminiClient.call_gemini(system_prompt, user_prompt)

class HighLevelAgent(BaseAgent):
    def process(self, class_name, associations):
        # التركيز هنا على "فكرة الملف" والهدف العام منه (The Concept)
        system = (
            "You are a Senior Software Architect with 15+ years of experience. Your goal is to explain "
            "the high-level purpose and core concept of a file based on the class name and its relationships. "
            "Explain what this file does in the overall system context.\n\n"
            "Structure your response as follows:\n"
            "1. **Purpose**: What is the main goal/responsibility of this component?\n"
            "2. **Architecture**: How does it fit into the layered architecture?\n"
            "3. **Relationships**: Explain the has-a relationships and dependencies.\n"
            "4. **Example Scenario**: Provide a concrete example of how this component is used.\n"
            "5. **Key Methods**: Briefly explain the purpose of main methods.\n\n"
            "Use clear, professional language that would be understandable to both technical and non-technical stakeholders. "
            "Focus on business logic and system design rather than implementation details."
        )
        user = f"Class Name: {class_name}\nRelationships: {associations}"
        return self.ask_ai(system, user)

class LowLevelAgent(BaseAgent):
    def process(self, code_content):
        # التركيز هنا على "كل تعليمة" والشرح التقني التفصيلي (The Implementation)
        system = (
            "You are a Senior Developer. Your goal is to provide a detailed technical "
            "explanation for each function and logic block in the provided code. "
            "Describe the implementation details and what each part specifically executes."
        )
        user = f"Analyze the following code in detail:\n{code_content}"
        return self.ask_ai(system, user)

class VerifierAgent(BaseAgent):
    def verify(self, code, explanation):
        system = (
            "You are a QA Lead. Verify the accuracy of the explanation against the code. "
            "Correct any technical errors or hallucinations to ensure the documentation is 100% correct."
        )
        user = f"Code: {code}\nExplanation to verify: {explanation}"
        return self.ask_ai(system, user)