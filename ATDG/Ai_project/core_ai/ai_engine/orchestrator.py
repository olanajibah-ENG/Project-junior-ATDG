from ..mongo_utils import get_mongo_db
from .agents import HighLevelAgent, LowLevelAgent, VerifierAgent
from bson import ObjectId
from datetime import datetime
from django.conf import settings

class DocumentationOrchestrator:
    def __init__(self, analysis_id):
        self.analysis_id = analysis_id
        self.db = get_mongo_db()
        self.collection = self.db[getattr(settings, 'AI_EXPLANATIONS_COLLECTION', 'ai_explanations')]

    def get_or_generate_explanation(self, exp_type):
        is_high_level = exp_type in ['high', 'high_level']
        normalized_exp_type = 'high_level' if is_high_level else 'low_level'
        
        existing = self.collection.find_one({
            "analysis_id": ObjectId(self.analysis_id),
            "exp_type": normalized_exp_type  # تصحيح: exp_type بدلاً من explanation_type
        })
        if not existing:
            existing = self.collection.find_one({
                "analysis_id": ObjectId(self.analysis_id),
                "exp_type": exp_type  # تصحيح: exp_type بدلاً من explanation_type
            })
        if not existing:
            existing = self.collection.find_one({
                "analysis_id": ObjectId(self.analysis_id),
                "explanation_type": normalized_exp_type  # الحقل القديم
            })
        if not existing:
            existing = self.collection.find_one({
                "analysis_id": ObjectId(self.analysis_id),
                "explanation_type": exp_type  # الحقل القديم
            })
        
        if existing:
            return existing['content'], str(existing['_id'])

        analysis_data = self.db[settings.ANALYSIS_RESULTS_COLLECTION].find_one(
            {"_id": ObjectId(self.analysis_id)}
        )
        if not analysis_data:
            raise Exception("Analysis record not found.")

        code_content = analysis_data.get('ast_structure', {}).get('code_content', '')
        
        semantic_data = analysis_data.get('semantic_analysis_data', {})
        extracted_features = analysis_data.get('extracted_features', {})
        class_diagram_data = analysis_data.get('class_diagram_data', {})
        
        
        if is_high_level:
            print(f"--- DEBUG: [Orchestrator] Generating HIGH LEVEL explanation for analysis_id: {self.analysis_id} ---")
            agent = HighLevelAgent()
            classes = class_diagram_data.get('classes', [])
            if classes:
                class_name = classes[0].get('name', 'Unknown')
            else:
                class_name = None

            analysis_summary = self._prepare_high_level_summary(semantic_data, class_diagram_data, extracted_features)

            try:
                raw_content = agent.process(
                    code_content,
                    class_name=class_name,
                    analysis_summary=analysis_summary
                )
                print(f"--- DEBUG: [Orchestrator] High level agent generated content (length: {len(raw_content)}) ---")
            except Exception as agent_error:
                error_msg = str(agent_error)
                print(f"--- DEBUG: [Orchestrator] High level agent failed: {error_msg} ---")
                raise Exception(f"Failed to generate High Level explanation: {error_msg}")
        else:
            print(f"--- DEBUG: [Orchestrator] Generating LOW LEVEL explanation for analysis_id: {self.analysis_id} ---")
            agent = LowLevelAgent()
            
            detailed_analysis = self._prepare_low_level_analysis(semantic_data, class_diagram_data, extracted_features)
            
            try:
                raw_content = agent.process(code_content, detailed_analysis=detailed_analysis)
                print(f"--- DEBUG: [Orchestrator] Low level agent generated content (length: {len(raw_content)}) ---")
            except Exception as agent_error:
                error_msg = str(agent_error)
                print(f"--- DEBUG: [Orchestrator] Low level agent failed: {error_msg} ---")
                raise Exception(f"Failed to generate Low Level explanation: {error_msg}")

        code_size = len(code_content) + len(raw_content)
        verifier = VerifierAgent()

        try:
            verified_content = verifier.verify(code=code_content, explanation=raw_content)
            print(f"--- DEBUG: [Orchestrator] Verification successful ---")

        except Exception as verify_error:
            error_msg = str(verify_error)
            print(f"--- DEBUG: [Orchestrator] Verification failed: {error_msg}")

            if "حجم الكود كبير" in error_msg or code_size > 100000:
                try:
                    verified_content = verifier.verify_async(code=code_content, explanation=raw_content)
                    print(f"--- DEBUG: [Orchestrator] Async verification successful for large code ---")
                except Exception as async_error:
                    print(f"--- DEBUG: [Orchestrator] Async verification also failed: {str(async_error)}. Using original with warning.")

                    warning_message = "⚠️ **Important Warning:** This is a preliminary explanation generated by AI and has not been verified for accuracy.\n"
                    warning_message += f"Reason for no verification: Code size too large ({code_size} characters) - may affect performance and accuracy.\n"
                    warning_message += f"Error details: {error_msg}\n"
                    warning_message += "Please review the content carefully before relying on it.\n\n---\n\n"

                    verified_content = warning_message + raw_content
            else:
                print(f"--- DEBUG: [Orchestrator] Non-size related verification error. Using original with warning.")

                warning_message = "⚠️ **Important Warning:** This is a preliminary explanation generated by AI and has not been verified for accuracy.\n"
                warning_message += f"Reason for no verification: {error_msg}\n"
                warning_message += "Please review the content carefully before relying on it.\n\n---\n\n"

                verified_content = warning_message + raw_content

        normalized_exp_type = 'high_level' if is_high_level else 'low_level'
        
        new_doc = {
            "analysis_id": ObjectId(self.analysis_id),
            "exp_type": normalized_exp_type,  # تصحيح: exp_type بدلاً من explanation_type
            "explanation_type": normalized_exp_type,  # الحقل القديم للتوافق
            "content": verified_content,
            "created_at": datetime.utcnow(),
            "code_content": code_content,  # حفظ الكود الأصلي للمراجعة
            "agent_type": "HighLevelAgent" if is_high_level else "LowLevelAgent"  # تحديد نوع الوكيل
        }

        print(f"--- DEBUG: [Orchestrator] Attempting to save {exp_type} explanation to MongoDB ---")
        print(f"--- DEBUG: [Orchestrator] Document to save: {new_doc.keys()} ---")

        result = self.collection.insert_one(new_doc)

        print(f"--- DEBUG: [Orchestrator] ✅ {exp_type.upper()} explanation saved successfully with ID: {result.inserted_id} ---")
        print(f"--- DEBUG: [Orchestrator] Agent type: {new_doc['agent_type']} ---")

        return verified_content, str(result.inserted_id)
    
    def _prepare_high_level_summary(self, semantic_data, class_diagram_data, extracted_features):
        """إعداد ملخص بسيط للتحليل للمستوى العالي (أسماء فقط)"""
        summary_parts = []
        
        classes = semantic_data.get('classes', []) or class_diagram_data.get('classes', [])
        if classes:
            class_names = [cls.get('name', 'Unknown') for cls in classes if isinstance(cls, dict)]
            if class_names:
                summary_parts.append(f"Classes found: {', '.join(class_names)}")
        
        if classes:
            all_methods = []
            for cls in classes:
                if isinstance(cls, dict):
                    methods = cls.get('methods', [])
                    if methods:
                        method_names = [m if isinstance(m, str) else m.get('name', '') for m in methods]
                        all_methods.extend(method_names)
            if all_methods:
                summary_parts.append(f"Main methods/functions: {', '.join(set(all_methods[:10]))}")  # أول 10 فقط
        
        if extracted_features:
            loc = extracted_features.get('lines_of_code', 0)
            func_count = extracted_features.get('functions', 0) or extracted_features.get('methods', 0)
            if loc or func_count:
                summary_parts.append(f"Code statistics: {loc} lines, {func_count} functions/methods")
        
        return "\n".join(summary_parts) if summary_parts else None
    
    def _prepare_low_level_analysis(self, semantic_data, class_diagram_data, extracted_features):
        """إعداد تحليل تفصيلي للمستوى المنخفض مع التركيز على العلاقات والوراثة"""
        analysis_parts = []
        
        classes = semantic_data.get('classes', []) or class_diagram_data.get('classes', [])
        if classes:
            analysis_parts.append("=== CLASSES AND RELATIONSHIPS ===")
            
            inheritance_map = {}
            composition_map = {}
            
            for cls in classes:
                if isinstance(cls, dict):
                    class_name = cls.get('name', 'Unknown')
                    
                    inherits = cls.get('inherits', []) or cls.get('inheritance', [])
                    if inherits:
                        inheritance_map[class_name] = inherits
                    
                    associations = cls.get('associations', []) or cls.get('relationships', [])
                    if associations:
                        composition_map[class_name] = associations
            
            if inheritance_map or composition_map:
                analysis_parts.append("\n** RELATIONSHIP ANALYSIS **")
                
                if inheritance_map:
                    analysis_parts.append("Inheritance Relationships:")
                    for child, parents in inheritance_map.items():
                        parents_str = ', '.join(parents) if isinstance(parents, list) else str(parents)
                        analysis_parts.append(f"  - {child} inherits from: {parents_str}")
                
                if composition_map:
                    analysis_parts.append("Composition/Association Relationships:")
                    for class_name, assocs in composition_map.items():
                        for assoc in assocs:
                            if isinstance(assoc, dict):
                                target = assoc.get('target_class', assoc.get('target', 'Unknown'))
                                rel_type = assoc.get('type', 'association')
                                analysis_parts.append(f"  - {class_name} --{rel_type}--> {target}")
            
            analysis_parts.append("\n** DETAILED CLASS ANALYSIS **")
            for cls in classes:
                if not isinstance(cls, dict): continue
                
                class_name = cls.get('name', 'Unknown')
                methods = cls.get('methods', [])
                attributes = cls.get('attributes', []) or cls.get('properties', [])
                
                header = f"\nClass: {class_name}"
                if class_name in inheritance_map:
                    header += f" (extends: {', '.join(inheritance_map[class_name])})"
                analysis_parts.append(header)
                
                if attributes:
                    analysis_parts.append("  Attributes/Properties:")
                    for attr in attributes:
                        if isinstance(attr, dict):
                            name = attr.get('name', '')
                            atype = attr.get('type', 'Any')
                            vis = attr.get('visibility', 'public')
                            analysis_parts.append(f"    - {vis} {name}: {atype}")
                        else:
                            analysis_parts.append(f"    - {attr}")
                
                if methods:
                    analysis_parts.append("  Methods:")
                    for method in methods:
                        if isinstance(method, dict):
                            m_name = method.get('name', '')
                            m_params = method.get('parameters', [])
                            m_ret = method.get('return_type', 'void')
                            m_vis = method.get('visibility', 'public')
                            
                            p_list = []
                            for p in m_params:
                                if isinstance(p, dict):
                                    p_list.append(f"{p.get('name')}: {p.get('type', 'Any')}")
                                else: p_list.append(str(p))
                            
                            analysis_parts.append(f"    - {m_vis} {m_name}({', '.join(p_list)}) -> {m_ret}")
                        else:
                            analysis_parts.append(f"    - {method}()")

        if extracted_features:
            analysis_parts.append("\n=== CODE COMPLEXITY & STATS ===")
            metrics = {
                "Lines of Code": extracted_features.get('lines_of_code'),
                "Total Methods": extracted_features.get('functions') or extracted_features.get('methods'),
                "Complexity Index": extracted_features.get('complexity', {}).get('cyclomatic_complexity')
            }
            for label, val in metrics.items():
                if val: analysis_parts.append(f"{label}: {val}")

        return "\n".join(analysis_parts) if analysis_parts else None
    
    def _detect_design_patterns(self, classes):
        """كشف أنماط التصميم المحتملة من بنية الفئات"""
        patterns = []
        
        if not classes:
            return patterns
        
        class_names = []
        inheritance_count = 0
        factory_indicators = []
        singleton_indicators = []
        
        for cls in classes:
            if isinstance(cls, dict):
                class_name = cls.get('name', '')
                class_names.append(class_name.lower())
                
                if any(keyword in class_name.lower() for keyword in ['factory', 'builder', 'creator']):
                    factory_indicators.append(class_name)
                
                methods = cls.get('methods', [])
                method_names = []
                if methods:
                    for method in methods:
                        if isinstance(method, str):
                            method_names.append(method.lower())
                        elif isinstance(method, dict):
                            method_names.append(method.get('name', '').lower())
                
                if 'getinstance' in method_names or 'instance' in method_names:
                    singleton_indicators.append(class_name)
                
                inherits = cls.get('inherits', []) or cls.get('inheritance', []) or cls.get('bases', [])
                if inherits:
                    inheritance_count += 1
        
        if factory_indicators:
            patterns.append(f"Factory Pattern detected in: {', '.join(factory_indicators)}")
        
        if singleton_indicators:
            patterns.append(f"Singleton Pattern detected in: {', '.join(singleton_indicators)}")
        
        if inheritance_count > 1:
            patterns.append(f"Inheritance hierarchy detected ({inheritance_count} classes with inheritance)")
        
        if any('adapter' in name for name in class_names):
            patterns.append("Adapter Pattern detected")
        
        if any('observer' in name for name in class_names):
            patterns.append("Observer Pattern detected")
        
        if any('strategy' in name for name in class_names):
            patterns.append("Strategy Pattern detected")
        
        return patterns