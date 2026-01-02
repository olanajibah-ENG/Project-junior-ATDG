from .base_processor import ILanguageProcessorStrategy
from typing import Dict, Any
import logging
import ast 

logger = logging.getLogger(__name__)


class PythonProcessor(ILanguageProcessorStrategy):
    def parse_source_code(self, code_content: str) -> Dict[str, Any]:
        logger.info("Parsing Python source code...")
        try:
            # التحليل الفعلي للكود
            tree = ast.parse(code_content)
            
            # (نحتاج إلى تحويل الشجرة إلى تمثيل يمكن حفظه في MongoDB، لكن سنُرجع الشجرة نفسها للتمرير)
            return {"ast_tree": tree,"code_content":code_content} # نستخدم ast_tree بدلاً من ast لتجنب الخلط
        except SyntaxError as e:
            logger.error(f"Failed to parse Python code (Syntax Error): {e}")
            return {"ast_tree": None, "error": str(e)}

    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Extracting Python features...")
        tree = ast_data.get("ast_tree")
        code_content=ast_data.get("code_content","") 
        if not tree:
            return {"lines_of_code": 0, "functions": 0}

        loc = len(code_content.splitlines()) if code_content else 0

        num_functions = 0
       
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                num_functions += 1
            if isinstance(node, ast.ClassDef):
                # نعد توابع الفئة أيضاً
                num_functions += sum(1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))

       
        return {"lines_of_code": loc, "functions": num_functions}


    def extract_dependencies(self, ast_data: Dict[str, Any]) -> list[str]: # تم تغيير نوع الإرجاع ليتطابق مع ما هو متوقع في النموذج
        logger.info("Extracting Python dependencies...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return []

        dependencies = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0: # استيراد خارجي/مطلق
                    dependencies.add(node.module.split('.')[0])
        
        return sorted(list(dependencies))
        
        

    def perform_semantic_analysis(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Performing Python semantic analysis...")
        return {"issues": [{"type": "warning", "message": "Unused import"}]}

    def generate_class_diagram_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating Python class diagram data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"classes": []}

        classes_data = []

        # 🟢 1. إنشاء قاموس مؤقت لتخزين جميع بيانات الفئات للوصول إليها لاحقًا
        temp_classes_map = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = []
                attributes = []
                associations = [] # 🟢 2. قائمة جديدة لتخزين علاقات التركيب/التجميع

                # استخراج الوراثة (Inheritance)
                base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]

                # استخراج الخصائص (Attributes) والدوال المنهجية (Methods) والعلاقات
                for item in node.body:
                    # استخراج الخصائص على مستوى الفئة (class attributes)
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attr_name = target.id
                                # تخمين نوع البيانات
                                attr_type = "Any"
                                if isinstance(item.value, ast.Str):
                                    attr_type = "str"
                                elif isinstance(item.value, ast.Num):
                                    attr_type = "int" if isinstance(item.value.n, int) else "float"
                                elif isinstance(item.value, ast.List):
                                    attr_type = "list"
                                elif isinstance(item.value, ast.Dict):
                                    attr_type = "dict"

                                attributes.append({
                                    "name": attr_name,
                                    "type": attr_type,
                                    "visibility": "public"
                                })

                    elif isinstance(item, ast.FunctionDef):
                        method_signature = f"{item.name}({', '.join([a.arg for a in item.args.args])})"
                        methods.append(method_signature)

                        # استخراج علاقات Association من parameters
                        for arg in item.args.args:
                            if arg.arg != 'self':  # تجاهل self
                                arg_type = getattr(arg, 'annotation', None)
                                if arg_type and isinstance(arg_type, ast.Name):
                                    # إذا كان الـ parameter من نوع فئة، فهي علاقة Association
                                    param_type = arg_type.id
                                    if param_type[0].isupper():  # افتراض أن الفئات تبدأ بحرف كبير
                                        associations.append({
                                            "target_class": param_type,
                                            "type": "Association",
                                            "attribute": arg.arg
                                        })

                        # 🟢 3. تحليل دالة التهيئة (__init__) للبحث عن الخصائص والعلاقات
                        if item.name == '__init__':
                            for sub_node in ast.walk(item):
                                # البحث عن التعيينات (Assignments) مثل self.engine = Engine(...)
                                if isinstance(sub_node, ast.Assign):
                                    # التحقق من أن الطرف الأيسر هو self.attribute
                                    if len(sub_node.targets) == 1 and isinstance(sub_node.targets[0], ast.Attribute) and isinstance(sub_node.targets[0].value, ast.Name) and sub_node.targets[0].value.id == 'self':
                                        attribute_name = sub_node.targets[0].attr

                                        # تخمين نوع الخاصية
                                        attr_type = "Any"
                                        if isinstance(sub_node.value, ast.Str):
                                            attr_type = "str"
                                        elif isinstance(sub_node.value, ast.Num):
                                            attr_type = "int" if isinstance(sub_node.value.n, int) else "float"
                                        elif isinstance(sub_node.value, ast.List):
                                            attr_type = "list"
                                        elif isinstance(sub_node.value, ast.Dict):
                                            attr_type = "dict"
                                        elif isinstance(sub_node.value, ast.Call) and isinstance(sub_node.value.func, ast.Name):
                                            # إذا كان استدعاء فئة، فهو composition
                                            target_class_name = sub_node.value.func.id
                                            attr_type = target_class_name

                                            # تسجيل العلاقة: (Composition/تكوين)
                                            associations.append({
                                                "target_class": target_class_name,
                                                "type": "Composition",
                                                "attribute": attribute_name
                                            })

                                        # إضافة الخاصية للقائمة
                                        attributes.append({
                                            "name": attribute_name,
                                            "type": attr_type,
                                            "visibility": "private"
                                        })

                class_data = {
                    "name": class_name,
                    "methods": methods,
                    "inherits": base_classes if base_classes else None,
                    "attributes": attributes, # سيتم تطوير هذا لاحقاً
                    "associations": associations # 🟢 4. إضافة العلاقات المستنتجة
                }

                temp_classes_map[class_name] = class_data # تخزين البيانات في القاموس المؤقت

        # 🟢 5. إرجاع قائمة القيم من القاموس
        return {"classes": list(temp_classes_map.values())}
        

    def generate_dependency_graph_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating Python dependency graph data...")
        # إرجاع قاموس فارغ أو نموذج بسيط
        return {"nodes": [], "edges": []}     