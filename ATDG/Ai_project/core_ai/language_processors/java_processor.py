from .base_processor import ILanguageProcessorStrategy
from typing import Dict, Any
import logging
from tree_sitter import Parser
try:
    import tree_sitter_java
    USE_DIRECT_IMPORT = True
except ImportError:
    USE_DIRECT_IMPORT = False

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
        try:
            if USE_LANGUAGES_LIB:
                logger.info("Using tree-sitter-languages for Java")
                self._java_language = get_language('java')
                logger.info("Java language loaded successfully via tree-sitter-languages")
            elif USE_DIRECT_IMPORT:
                logger.info("Using direct tree-sitter-java import")
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
            tree = self._internal_java_parser.parse(code_content.encode('utf8'))

            return {"ast_tree": tree,"code_content":code_content}

        except Exception as e:
            logger.error(f"Failed to parse Java code: {e}")
            return {"ast_tree": None, "error": str(e)} 

    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Extracting Java features...")
        tree = ast_data.get("ast_tree")
        code_content = ast_data.get("code_content", "") 
        if not tree:
            return {"lines_of_code": 0, "functions": 0}

        loc = len(code_content.splitlines()) if code_content else 0
        num_methods = 0
        num_classes = 0
        num_constructors = 0
        function_details = []
       
        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node
            
            if node.type == 'method_declaration':
                num_methods += 1
                method_name = self._extract_method_name(node)
                function_details.append({
                    'name': method_name,
                    'line': node.start_point[0] + 1,
                    'is_method': True,
                    'is_async': False
                })
            elif node.type == 'constructor_declaration':
                num_constructors += 1
                constructor_name = "constructor"
                for child in node.children:
                    if child.type == 'identifier':
                        constructor_name = child.text.decode('utf-8')
                        break
                function_details.append({
                    'name': constructor_name,
                    'line': node.start_point[0] + 1,
                    'is_method': True,
                    'is_constructor': True,
                    'is_async': False
                })
            elif node.type == 'class_declaration':
                num_classes += 1

            if cursor.goto_first_child():
                continue
            if cursor.goto_next_sibling():
                continue
            while cursor.goto_parent():
                if cursor.goto_next_sibling():
                    break
            else:
                reached_root = True
        
        total_functions = num_methods + num_constructors
        
        return {
            "lines_of_code": loc, 
            "functions": total_functions,  # إجمالي الطرق والـ constructors
            "standalone_functions": 0,  # Java doesn't have standalone functions
            "methods": num_methods,
            "constructors": num_constructors,
            "classes": num_classes,
            "function_details": function_details
        }

    def _extract_method_name(self, method_node) -> str:
        """استخراج اسم الطريقة من عقدة method_declaration"""
        for child in method_node.children:
            if child.type == 'identifier':
                return child.text.decode('utf-8')
        return "unknown_method" 


    def extract_dependencies(self, ast_data: Dict[str, Any]) -> list[str]:
        logger.info("Extracting Java dependencies...")
        tree = ast_data.get("ast_tree")
        code_content = ast_data.get("code_content", "")
        if not tree:
            return []

        dependencies = []

        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node

            if node.type == 'import_declaration':
                import_parts = []
                has_asterisk = False

                for child in node.children:
                    if child.type == 'identifier':
                        import_parts.append(child.text.decode('utf-8'))
                    elif child.type == 'scoped_identifier':
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
        abstract_classes = []

        cursor = tree.walk()
        reached_root = False
        while reached_root == False:
            node = cursor.node

            if node.type == 'class_declaration':
                is_abstract = False
                class_name = ""
                
                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'modifiers':
                        for modifier in child.children:
                            if modifier.type == 'abstract':
                                is_abstract = True
                                break
                
                if is_abstract and class_name:
                    abstract_classes.append(class_name)
                    issues.append({
                        "type": "info",
                        "message": f"Abstract class detected: {class_name}",
                        "category": "abstract_class"
                    })

            elif node.type == 'variable_declarator':
                has_initializer = False
                var_name = ""
                
                for child in node.children:
                    if child.type == 'variable_initializer':
                        has_initializer = True
                    elif child.type == 'identifier':
                        var_name = child.text.decode('utf-8')

                if not has_initializer and var_name:
                    issues.append({
                        "type": "warning",
                        "message": f"Variable '{var_name}' is declared but not initialized",
                        "line": node.start_point[0] + 1,
                        "category": "uninitialized_variable"
                    })

            elif node.type == 'method_invocation':
                method_name = ""
                identifiers = []
                for child in node.children:
                    if child.type == 'identifier':
                        identifiers.append(child.text.decode('utf-8'))

                if identifiers:
                    method_name = identifiers[-1]
                    deprecated_methods = ['Thread.stop', 'Thread.suspend', 'Thread.resume']
                    for deprecated in deprecated_methods:
                        if deprecated in method_name:
                            issues.append({
                                "type": "warning",
                                "message": f"Usage of deprecated method '{method_name}'",
                                "line": node.start_point[0] + 1,
                                "category": "deprecated_api"
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

        if "NullPointerException" in code_content:
            issues.append({
                "type": "info",
                "message": "Code contains NullPointerException handling",
                "category": "exception_handling"
            })

        return {
            "issues": issues,
            "abstract_classes": abstract_classes,
            "imports_analysis": {}  # Java doesn't have the same import analysis as Python
        }

    def generate_class_diagram_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating Java class diagram data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"classes": []}

        classes_data = []
        temp_classes_map = {}

        cursor = tree.walk()
        reached_root = False

        while reached_root == False:
            node = cursor.node

            if node.type == 'class_declaration':
                class_name = ""
                methods = []
                attributes = []
                associations = []

                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break

                base_classes = []
                for child in node.children:
                    if child.type == 'superclass':
                        for subchild in child.children:
                            if subchild.type == 'type_identifier':
                                base_classes.append(subchild.text.decode('utf-8'))

                for child in node.children:
                    if child.type == 'class_body':
                        for item in child.children:
                            if item.type == 'field_declaration':
                                field_info = self._extract_field_info(item)
                                if field_info:
                                    attributes.append(field_info)

                                field_associations = self._extract_field_associations(item)
                                associations.extend(field_associations)

                            elif item.type == 'method_declaration':
                                method_info = self._extract_method_info(item)
                                if method_info:
                                    methods.append(method_info)

                            elif item.type == 'constructor_declaration':
                                constructor_associations = self._extract_constructor_associations(item)
                                associations.extend(constructor_associations)

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
                    "associations": self._deduplicate_associations(associations)  # إزالة التكرار
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

        if field_type and field_name and field_type[0].isupper():
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
        classes_found = set()
        imports_found = set()

        cursor = tree.walk()
        reached_root = False

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
                        "type": "class",
                        "local": True
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

        dependencies = self.extract_dependencies(ast_data)
        for dep in dependencies:
            if dep not in imports_found:
                imports_found.add(dep)
                nodes.append({
                    "id": dep,
                    "label": dep,
                    "type": "module",
                    "local": False
                })

        for class_name in classes_found:
            for dep in dependencies:
                edges.append({
                    "source": class_name,
                    "target": dep,
                    "type": "dependency"
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "local_classes": len([n for n in nodes if n.get('local', False)]),
                "external_modules": len([n for n in nodes if not n.get('local', True)])
            }
        }

    def _deduplicate_associations(self, associations: list) -> list:
        """إزالة تكرار العلاقات في Java"""
        seen = set()
        unique_associations = []
        
        for assoc in associations:
            key = (assoc['target_class'], assoc['type'], assoc['attribute'])
            if key not in seen:
                seen.add(key)
                unique_associations.append(assoc)
        
        logger.info(f"Java: Deduplicated associations: {len(associations)} -> {len(unique_associations)}")
        return unique_associations     