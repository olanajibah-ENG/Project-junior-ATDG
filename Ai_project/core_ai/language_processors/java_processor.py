# C:\مواد\Kamar_11_2025\Ai_project\core_ai\language_processors\java_processor.py
from .base_processor import ILanguageProcessorStrategy
from typing import Dict, Any
import logging
from tree_sitter import Parser
try:
    import tree_sitter_java
    USE_DIRECT_IMPORT = True
except ImportError:
    USE_DIRECT_IMPORT = False

# Always try tree_sitter_languages first as it's more reliable
try:
    from tree_sitter_languages import get_language
    USE_LANGUAGES_LIB = True
except ImportError:
    USE_LANGUAGES_LIB = False

logger = logging.getLogger(__name__)

class JavaProcessor(ILanguageProcessorStrategy):

    def __init__(self):
        self.init()

    def init(self):
        # 2. تهيئة المُحلل وتحميل لغة Java باستخدام tree-sitter-languages أو tree-sitter-java
        try:
            # Prefer tree_sitter_languages as it's more reliable
            if USE_LANGUAGES_LIB:
                logger.info("Using tree-sitter-languages for Java")
                self._java_language = get_language('java')
                logger.info("Java language loaded successfully via tree-sitter-languages")
            elif USE_DIRECT_IMPORT:
                logger.info("Using direct tree-sitter-java import")
                # Direct usage without Language wrapper
                self._java_language = tree_sitter_java.language()
                logger.info("Java language loaded directly from tree_sitter_java.language()")
            else:
                raise ImportError("Neither tree-sitter-languages nor tree-sitter-java available")

            self._internal_java_parser = Parser()
            self._internal_java_parser.set_language(self._java_language)  # Use set_language method
            logger.info("Java Tree-sitter language loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Java Tree-sitter language: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._java_language = None
            self._internal_java_parser = None
        
    def parse_source_code(self, code_content: str) -> Dict[str, Any]:
        logger.info("Parsing Java source code...")
        if not self._java_language or not self._internal_java_parser:
            return {"ast_tree": None, "error": "Java parser not initialized (Tree-sitter language file missing)"}

        try:
            # يجب ترميز الكود إلى Bytes
            tree = self._internal_java_parser.parse(code_content.encode('utf8'))

            return {"ast_tree": tree,"code_content":code_content}

        except Exception as e:
            logger.error(f"Failed to parse Java code: {e}")
            return {"ast_tree": None, "error": str(e)} 

    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Extracting Java features...")
        tree = ast_data.get("ast_tree")
        code_content=ast_data.get("code_content","") 
        if not tree:
            return {"lines_of_code": 0, "methods": 0}

        loc = len(code_content.splitlines()) if code_content else 0
        num_methods = 0
       
        # 🟢 4. منطق التنقل في شجرة Tree-sitter
        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node
            
            if node.type == 'method_declaration': # أو 'function_definition' حسب قاعدة اللغة
                num_methods += 1

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break
                
            else:
                reached_root = True
        
        # إرجاع الخصائص المستخرجة
        return {"lines_of_code": loc, "methods": num_methods} 


    def extract_dependencies(self, ast_data: Dict[str, Any]) -> list[str]:
        logger.info("Extracting Java dependencies...")
        tree = ast_data.get("ast_tree")
        code_content = ast_data.get("code_content", "")
        if not tree:
            return []

        dependencies = []

        # استخراج imports من شجرة AST
        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node

            if node.type == 'import_declaration':
                # استخراج اسم الـ import
                import_parts = []
                has_asterisk = False

                for child in node.children:
                    if child.type == 'identifier':
                        import_parts.append(child.text.decode('utf-8'))
                    elif child.type == 'scoped_identifier':
                        # scoped_identifier يحتوي على النقاط، لكن يجب تجزئته
                        scoped_text = child.text.decode('utf-8')
                        scoped_parts = scoped_text.split('.')
                        import_parts.extend(scoped_parts)
                    elif child.type == 'asterisk':
                        has_asterisk = True

                if import_parts:
                    import_text = '.'.join(import_parts)
                    if has_asterisk:
                        import_text += ".*"

                    if import_text not in dependencies:
                        dependencies.append(import_text)

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break

            else:
                reached_root = True

        # إذا لم نجد imports في AST، نحاول استخراجها من النص مباشرة كـ fallback
        if not dependencies and code_content:
            lines = code_content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import '):
                    import_stmt = line[7:].strip()  # إزالة 'import '
                    if import_stmt.endswith(';'):
                        import_stmt = import_stmt[:-1]  # إزالة ';'
                    if import_stmt and import_stmt not in dependencies:
                        dependencies.append(import_stmt)

        return dependencies 

    def perform_semantic_analysis(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Performing Java semantic analysis...")
        tree = ast_data.get("ast_tree")
        code_content = ast_data.get("code_content", "")
        if not tree:
            return {"issues": []}

        issues = []

        # البحث عن مشاكل محتملة في شجرة AST
        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node

            # البحث عن استخدام null checks
            if node.type == 'binary_expression':
                # التحقق من == null أو != null
                left_side = None
                operator = None
                right_side = None

                for child in node.children:
                    if child.type in ['identifier', 'field_access', 'method_invocation']:
                        if left_side is None:
                            left_side = child
                        elif right_side is None:
                            right_side = child
                    elif child.type in ['==', '!=']:
                        operator = child.text.decode('utf-8')

                if operator and ((left_side and right_side and right_side.type == 'null_literal') or
                                (right_side and left_side and left_side.type == 'null_literal')):
                    # تم العثور على null check
                    pass  # يمكن تحسين هذا لاحقاً

            # البحث عن استدعاءات methods على متغيرات قد تكون null
            elif node.type == 'method_invocation':
                object_part = None
                method_name = None

                for child in node.children:
                    if child.type == 'identifier':
                        if method_name is None:
                            method_name = child.text.decode('utf-8')
                    elif child.type == 'field_access':
                        object_part = child
                        # استخراج اسم المتغير المُستدعى عليه الـ method
                        for field_child in child.children:
                            if field_child.type == 'identifier':
                                object_name = field_child.text.decode('utf-8')
                                # هنا يمكن إضافة منطق للتحقق من إمكانية كون المتغير null
                                break

            # البحث عن استخدام متغيرات غير مُهيأة
            elif node.type == 'variable_declarator':
                # التحقق من وجود initializer
                has_initializer = False
                for child in node.children:
                    if child.type == 'variable_initializer':
                        has_initializer = True
                        break

                if not has_initializer:
                    # استخراج اسم المتغير
                    var_name = ""
                    for child in node.children:
                        if child.type == 'identifier':
                            var_name = child.text.decode('utf-8')
                            break

                    if var_name:
                        issues.append({
                            "type": "warning",
                            "message": f"Variable '{var_name}' is declared but not initialized",
                            "line": node.start_point[0] + 1
                        })

            # البحث عن استخدام deprecated APIs (مثال بسيط)
            elif node.type == 'method_invocation':
                method_name = ""
                # استخراج اسم الطريقة (آخر identifier في method_invocation)
                identifiers = []
                for child in node.children:
                    if child.type == 'identifier':
                        identifiers.append(child.text.decode('utf-8'))

                if identifiers:
                    method_name = identifiers[-1]  # آخر identifier هو اسم الطريقة

                # قائمة بسيطة من deprecated methods (يمكن توسيعها)
                deprecated_methods = ['Thread.stop', 'Thread.suspend', 'Thread.resume']
                for deprecated in deprecated_methods:
                    if deprecated in method_name:
                        issues.append({
                            "type": "warning",
                            "message": f"Usage of deprecated method '{method_name}'",
                            "line": node.start_point[0] + 1
                        })

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break

            else:
                reached_root = True

        # إضافة تحليلات بسيطة أخرى
        if "NullPointerException" in code_content:
            issues.append({
                "type": "info",
                "message": "Code contains NullPointerException handling",
                "line": 0
            })

        return {"issues": issues}

    def generate_class_diagram_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating Java class diagram data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"classes": []}

        classes_data = []
        temp_classes_map = {}

        # استخدام المنطق البسيط للتراجع مثل الطرق الأخرى
        cursor = tree.walk()
        reached_root = False

        while reached_root == False:
            node = cursor.node

            if node.type == 'class_declaration':
                class_name = ""
                methods = []
                attributes = []
                associations = []

                # استخراج اسم الفئة
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break

                # استخراج الوراثة (Inheritance)
                base_classes = []
                for child in node.children:
                    if child.type == 'superclass':
                        for subchild in child.children:
                            if subchild.type == 'type_identifier':
                                base_classes.append(subchild.text.decode('utf-8'))

                # استخراج الطرق والخصائص من class_body
                for child in node.children:
                    if child.type == 'class_body':
                        for item in child.children:
                            # استخراج الخصائص (field declarations)
                            if item.type == 'field_declaration':
                                field_info = self._extract_field_info(item)
                                if field_info:
                                    attributes.append(field_info)

                                # استخراج علاقات Association من نوع الخاصية
                                field_associations = self._extract_field_associations(item)
                                associations.extend(field_associations)

                            # استخراج الطرق (methods)
                            elif item.type == 'method_declaration':
                                method_info = self._extract_method_info(item)
                                if method_info:
                                    methods.append(method_info)

                            # استخراج البناء (constructors)
                            elif item.type == 'constructor_declaration':
                                constructor_associations = self._extract_constructor_associations(item)
                                associations.extend(constructor_associations)

                            # استخراج الطرق (methods) مع علاقات Association من parameters
                            elif item.type == 'method_declaration':
                                method_info = self._extract_method_info(item)
                                if method_info:
                                    methods.append(method_info)

                                method_param_associations = self._extract_method_parameters_associations(item)
                                associations.extend(method_param_associations)

                class_data = {
                    "name": class_name,
                    "methods": methods,
                    "inherits": base_classes if base_classes else None,
                    "attributes": attributes,
                    "associations": associations
                }

                if class_name:
                    temp_classes_map[class_name] = class_data

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break

            else:
                reached_root = True

        return {"classes": list(temp_classes_map.values())}

    def _extract_field_info(self, field_node) -> Dict[str, Any]:
        """استخراج معلومات الخاصية (field)"""
        field_type = ""
        field_name = ""
        visibility = "private"  # افتراضي

        for child in field_node.children:
            if child.type == 'modifiers':
                for modifier in child.children:
                    if modifier.type in ['public', 'private', 'protected']:
                        visibility = modifier.text.decode('utf-8')
            elif child.type == 'type_identifier':
                field_type = child.text.decode('utf-8')
            elif child.type == 'variable_declarator':
                for sub_child in child.children:
                    if sub_child.type == 'identifier':
                        field_name = sub_child.text.decode('utf-8')
                        break

        if field_name:
            return {
                "name": field_name,
                "type": field_type,
                "visibility": visibility
            }
        return None

    def _extract_method_info(self, method_node) -> str:
        """استخراج معلومات الطريقة (method)"""
        method_name = ""
        for child in method_node.children:
            if child.type == 'identifier':
                method_name = child.text.decode('utf-8')
                break
        return method_name if method_name else None

    def _extract_method_parameters_associations(self, method_node) -> list:
        """استخراج علاقات Association من parameters الطريقة"""
        associations = []

        for child in method_node.children:
            if child.type == 'formal_parameters':
                for param in child.children:
                    if param.type == 'formal_parameter':
                        param_type = ""
                        param_name = ""

                        for param_child in param.children:
                            if param_child.type == 'type_identifier':
                                param_type = param_child.text.decode('utf-8')
                            elif param_child.type == 'identifier':
                                param_name = param_child.text.decode('utf-8')

                        # إذا كان النوع يبدأ بحرف كبير (فئة)، فهي علاقة Association
                        if param_type and param_name and param_type[0].isupper():
                            associations.append({
                                "target_class": param_type,
                                "type": "Association",
                                "attribute": param_name
                            })

        return associations

    def _extract_constructor_associations(self, constructor_node) -> list:
        """استخراج علاقات التركيب من البناء"""
        associations = []

        constructor_body = None
        for child in constructor_node.children:
            if child.type == 'constructor_body':
                constructor_body = child
                break

        if constructor_body:
            for stmt in constructor_body.children:
                if stmt.type == 'expression_statement':
                    for expr in stmt.children:
                        if expr.type == 'assignment_expression':
                            field_name = None
                            class_name_target = None

                            # استخراج الجانب الأيسر (this.field)
                            for assign_child in expr.children:
                                if assign_child.type == 'field_access':
                                    has_this = False
                                    identifiers_after_this = []
                                    for field_part in assign_child.children:
                                        if field_part.type == 'this':
                                            has_this = True
                                        elif field_part.type == 'identifier' and has_this:
                                            identifiers_after_this.append(field_part.text.decode('utf-8'))

                                    if identifiers_after_this:
                                        field_name = identifiers_after_this[-1]  # آخر identifier هو اسم الـ field

                            # استخراج الجانب الأيمن (new ClassName(...))
                            for assign_child in expr.children:
                                if assign_child.type == 'object_creation_expression':
                                    for creation_part in assign_child.children:
                                        if creation_part.type == 'type_identifier':
                                            class_name_target = creation_part.text.decode('utf-8')
                                            break

                            if field_name and class_name_target:
                                associations.append({
                                    "target_class": class_name_target,
                                    "type": "Composition",
                                    "attribute": field_name
                                })

        return associations

    def _extract_field_associations(self, field_node) -> list:
        """استخراج علاقات Association من نوع الخاصية"""
        associations = []

        field_type = ""
        field_name = ""

        for child in field_node.children:
            if child.type == 'type_identifier':
                field_type = child.text.decode('utf-8')
            elif child.type == 'variable_declarator':
                for sub_child in child.children:
                    if sub_child.type == 'identifier':
                        field_name = sub_child.text.decode('utf-8')
                        break

        # إذا كان النوع يبدأ بحرف كبير ولم يتم إنشاؤه في البناء (ليس Composition)، فهي Association
        if field_type and field_name and field_type[0].isupper():
            # تحقق من أنه ليس primitive type
            primitive_types = ['int', 'long', 'short', 'byte', 'float', 'double', 'char', 'boolean', 'String']
            if field_type not in primitive_types:
                associations.append({
                    "target_class": field_type,
                    "type": "Association",
                    "attribute": field_name
                })

        return associations

    def generate_dependency_graph_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating Java dependency graph data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []

        # استخراج الفئات كـ nodes
        cursor = tree.walk()
        reached_root = False
        classes_found = set()

        while reached_root == False:
            node = cursor.node

            if node.type == 'class_declaration':
                class_name = ""
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break

                if class_name and class_name not in classes_found:
                    classes_found.add(class_name)
                    nodes.append({
                        "id": class_name,
                        "label": class_name,
                        "type": "class"
                    })

            if cursor.goto_first_child():
                continue

            if cursor.goto_next_sibling():
                continue

            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break

            else:
                reached_root = True

        # استخراج التبعيات من imports كـ edges
        dependencies = self.extract_dependencies(ast_data)
        # استخدام أول فئة كفئة رئيسية، أو MainClass كـ fallback
        main_class = next(iter(classes_found)) if classes_found else "MainClass"

        for dep in dependencies:
            # إنشاء edge بسيط للتبعية
            edges.append({
                "from": main_class,
                "to": dep.split('.')[-1],  # اسم الفئة الأخيرة في الـ import
                "label": "imports"
            })

        return {"nodes": nodes, "edges": edges}     