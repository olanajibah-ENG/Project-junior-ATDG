from .base_processor import ILanguageProcessorStrategy
from typing import Dict, Any, Set, List, Tuple
import logging
import ast
from collections import defaultdict

logger = logging.getLogger(__name__)


class PythonASTVisitor(ast.NodeVisitor):
    """زائر AST متخصص لتحليل دقيق للكود Python"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """إعادة تعيين جميع البيانات"""
        self.function_definitions = []
        self.method_definitions = []
        self.class_definitions = []
        
        self.classes_map = {}
        self.imports_map = {}
        self.dependencies = set()
        
        self.current_class = None
        self.in_class_context = False
        
        self.function_calls_ignored = 0
    
    def visit_Import(self, node):
        """معالجة import statements"""
        for alias in node.names:
            module_name = alias.name
            alias_name = alias.asname or alias.name
            root_module = module_name.split('.')[0]
            self.dependencies.add(root_module)
            self.imports_map[alias_name] = module_name
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """معالجة from ... import statements"""
        if node.module:
            root_module = node.module.split('.')[0]
            self.dependencies.add(root_module)
            for alias in node.names:
                imported_name = alias.name
                alias_name = alias.asname or alias.name
                self.imports_map[alias_name] = node.module
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """معالجة تعريفات الفئات"""
        old_class = self.current_class
        old_in_class = self.in_class_context
        
        self.current_class = node.name
        self.in_class_context = True
        
        class_info = {
            'name': node.name,
            'line': node.lineno,
            'methods': [],
            'attributes': [],
            'base_classes': [base.id for base in node.bases if isinstance(base, ast.Name)],
            'associations': []
        }
        
        self.class_definitions.append(class_info)
        self.classes_map[node.name] = class_info
        
        self.generic_visit(node)
        
        self.current_class = old_class
        self.in_class_context = old_in_class
    
    def visit_FunctionDef(self, node):
        """معالجة تعريفات الدوال والطرق - الحل الرئيسي للعد الخاطئ"""
        function_info = {
            'name': node.name,
            'line': node.lineno,
            'is_async': False,
            'parameters': [arg.arg for arg in node.args.args]
        }
        
        if self.in_class_context:
            function_info['is_method'] = True
            function_info['class_name'] = self.current_class
            self.method_definitions.append(function_info)
            
            if self.current_class in self.classes_map:
                method_signature = self._build_method_signature(node)
                self.classes_map[self.current_class]['methods'].append(method_signature)
                
                if node.name == '__init__':
                    self._analyze_init_method(node)
                
                self._analyze_method_parameters(node)
        else:
            function_info['is_method'] = False
            self.function_definitions.append(function_info)
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """معالجة الدوال غير المتزامنة"""
        function_info = {
            'name': node.name,
            'line': node.lineno,
            'is_async': True,
            'parameters': [arg.arg for arg in node.args.args]
        }
        
        if self.in_class_context:
            function_info['is_method'] = True
            function_info['class_name'] = self.current_class
            self.method_definitions.append(function_info)
            
            if self.current_class in self.classes_map:
                method_signature = self._build_method_signature(node)
                self.classes_map[self.current_class]['methods'].append(method_signature)
        else:
            function_info['is_method'] = False
            self.function_definitions.append(function_info)
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """معالجة استدعاءات الدوال - نتجاهلها في العد"""
        self.function_calls_ignored += 1
        self.generic_visit(node)
    
    def _build_method_signature(self, method_node):
        """بناء توقيع الطريقة"""
        args = []
        for arg in method_node.args.args:
            if arg.arg != 'self':
                arg_type = self._get_type_annotation(arg)
                if arg_type:
                    args.append(f"{arg.arg}: {arg_type}")
                else:
                    args.append(arg.arg)
        
        signature = f"{method_node.name}({', '.join(args)})"
        
        if hasattr(method_node, 'returns') and method_node.returns:
            return_type = self._get_annotation_name(method_node.returns)
            signature += f" -> {return_type}"
        
        return signature
    
    def _analyze_init_method(self, init_node):
        """تحليل طريقة __init__ للخصائص والعلاقات"""
        if not self.current_class:
            return
        
        class_info = self.classes_map[self.current_class]
        
        for node in ast.walk(init_node):
            if isinstance(node, ast.Assign):
                if (len(node.targets) == 1 and 
                    isinstance(node.targets[0], ast.Attribute) and
                    isinstance(node.targets[0].value, ast.Name) and 
                    node.targets[0].value.id == 'self'):
                    
                    attr_name = node.targets[0].attr
                    attr_type, relationship = self._analyze_attribute_value(node.value, attr_name)
                    
                    class_info['attributes'].append({
                        'name': attr_name,
                        'type': attr_type,
                        'visibility': 'private'
                    })
                    
                    if relationship:
                        class_info['associations'].append(relationship)
    
    def _analyze_attribute_value(self, value_node, attr_name):
        """تحليل قيمة الخاصية لتحديد النوع والعلاقة"""
        attr_type = "Any"
        relationship = None
        
        if isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                class_name = value_node.func.id
                if self._is_class_type(class_name):
                    attr_type = class_name
                    relationship = {
                        'target_class': class_name,
                        'type': 'Composition',
                        'attribute': attr_name,
                        'source': 'init_constructor_call'
                    }
        elif isinstance(value_node, ast.Name):
            var_name = value_node.id
            if var_name != 'self':
                relationship = {
                    'target_class': 'Unknown',
                    'type': 'Aggregation',
                    'attribute': attr_name,
                    'source': 'init_parameter_assignment'
                }
        elif isinstance(value_node, (ast.Str, ast.Constant)):
            if hasattr(value_node, 'value') and isinstance(value_node.value, str):
                attr_type = "str"
            elif hasattr(value_node, 's'):
                attr_type = "str"
        elif isinstance(value_node, (ast.Num, ast.Constant)):
            if hasattr(value_node, 'value') and isinstance(value_node.value, (int, float)):
                attr_type = "int" if isinstance(value_node.value, int) else "float"
            elif hasattr(value_node, 'n'):
                attr_type = "int" if isinstance(value_node.n, int) else "float"
        
        return attr_type, relationship
    
    def _analyze_method_parameters(self, method_node):
        """تحليل parameters للعلاقات"""
        if not self.current_class:
            return
        
        class_info = self.classes_map[self.current_class]
        
        for arg in method_node.args.args:
            if arg.arg != 'self':
                arg_type = self._get_type_annotation(arg)
                if arg_type and self._is_class_type(arg_type):
                    relationship = {
                        'target_class': arg_type,
                        'type': 'Association',
                        'attribute': arg.arg,
                        'source': f'method_{method_node.name}_parameter'
                    }
                    class_info['associations'].append(relationship)
    
    def _get_type_annotation(self, arg):
        """استخراج نوع البيانات من annotation"""
        if hasattr(arg, 'annotation') and arg.annotation:
            return self._get_annotation_name(arg.annotation)
        return None
    
    def _get_annotation_name(self, annotation):
        """تحويل annotation إلى اسم"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return self._get_full_name(annotation)
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        return "Any"
    
    def _get_full_name(self, attr_node):
        """الحصول على الاسم الكامل"""
        parts = []
        current = attr_node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))
    
    def _is_class_type(self, type_name):
        """تحديد ما إذا كان الاسم يمثل فئة"""
        return type_name and type_name[0].isupper()


class PythonProcessor(ILanguageProcessorStrategy):
    """
    معالج Python محسن باستخدام ast.NodeVisitor
    
    الحل الرئيسي للمشاكل:
    1. استخدام NodeVisitor بدلاً من ast.walk لعد دقيق
    2. التمييز بين تعريفات الدوال واستدعاءاتها
    3. تحليل العلاقات المتقدم (Composition, Aggregation, Dependency)
    4. استخراج الخصائص من __init__
    5. بناء dependency_graph فعال
    """
    
    def __init__(self):
        self.visitor = PythonASTVisitor()
        self.imports_map = {}
        self.classes_map = {}
        self.functions_map = {}
    
    def parse_source_code(self, code_content: str) -> Dict[str, Any]:
        """تحليل كود Python وإرجاع AST"""
        logger.info("Parsing Python source code with enhanced NodeVisitor processor...")
        try:
            tree = ast.parse(code_content)
            return {"ast_tree": tree, "code_content": code_content}
        except SyntaxError as e:
            logger.error(f"Failed to parse Python code (Syntax Error): {e}")
            return {"ast_tree": None, "error": str(e)}

    def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        """استخراج المميزات مع عد دقيق باستخدام NodeVisitor"""
        logger.info("Extracting Python features with NodeVisitor (accurate counting)...")
        tree = ast_data.get("ast_tree")
        code_content = ast_data.get("code_content", "")
        
        if not tree:
            return {"lines_of_code": 0, "functions": 0}

        loc = len(code_content.splitlines()) if code_content else 0
        
        self.visitor.reset()
        self.visitor.visit(tree)
        
        self.imports_map = self.visitor.imports_map.copy()
        self.classes_map = self.visitor.classes_map.copy()
        
        total_functions = len(self.visitor.function_definitions) + len(self.visitor.method_definitions)
        
        logger.info(f"Accurate count: {len(self.visitor.function_definitions)} standalone functions + {len(self.visitor.method_definitions)} methods = {total_functions} total")
        logger.info(f"Function calls ignored: {self.visitor.function_calls_ignored}")
        
        return {
            "lines_of_code": loc,
            "functions": total_functions,
            "standalone_functions": len(self.visitor.function_definitions),
            "methods": len(self.visitor.method_definitions),
            "classes": len(self.visitor.class_definitions),
            "function_details": self.visitor.function_definitions + self.visitor.method_definitions
        }


    def extract_dependencies(self, ast_data: Dict[str, Any]) -> List[str]:
        """استخراج التبعيات مع تحليل متقدم للاستيرادات"""
        logger.info("Extracting Python dependencies with enhanced analysis...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return []

        self.visitor.reset()
        self.visitor.visit(tree)
        
        self.dependencies = self.visitor.dependencies.copy()
        self.imports_map = self.visitor.imports_map.copy()

        return list(self.dependencies)

    def perform_semantic_analysis(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """تحليل دلالي متقدم للكود"""
        logger.info("Performing enhanced semantic analysis...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"issues": []}

        issues = []
        
        used_imports = set()
        defined_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_imports.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_imports.add(node.value.id)
            
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)

        for alias_name, module_name in self.imports_map.items():
            if alias_name not in used_imports:
                issues.append({
                    "type": "warning",
                    "message": f"Unused import: {module_name}",
                    "category": "unused_import"
                })

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append({
                        "type": "info",
                        "message": f"Empty function: {node.name}",
                        "line": node.lineno,
                        "category": "empty_function"
                    })

        abstract_classes = self._detect_abstract_classes(tree)
        for class_name in abstract_classes:
            issues.append({
                "type": "info",
                "message": f"Abstract class detected: {class_name}",
                "category": "abstract_class"
            })

        return {
            "issues": issues,
            "abstract_classes": list(abstract_classes),
            "imports_analysis": self.imports_map
        }

    def _detect_abstract_classes(self, tree: ast.AST) -> Set[str]:
        """اكتشاف الفئات التجريدية"""
        abstract_classes = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ['ABC', 'AbstractBase']:
                        abstract_classes.add(node.name)
                    elif isinstance(base, ast.Attribute):
                        if (isinstance(base.value, ast.Name) and 
                            base.value.id == 'abc' and base.attr == 'ABC'):
                            abstract_classes.add(node.name)
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                                abstract_classes.add(node.name)
                            elif isinstance(decorator, ast.Attribute):
                                if (isinstance(decorator.value, ast.Name) and 
                                    decorator.value.id == 'abc' and 
                                    decorator.attr == 'abstractmethod'):
                                    abstract_classes.add(node.name)
        
        return abstract_classes

    def generate_class_diagram_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """توليد بيانات مخطط الفئات مع إزالة التكرار وتحسين العلاقات"""
        logger.info("Generating enhanced Python class diagram data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"classes": []}

        classes_data = []
        self.classes_map = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node)
                self.classes_map[class_info['name']] = class_info
                classes_data.append(class_info)

        for class_data in classes_data:
            class_data['associations'] = self._deduplicate_associations(
                class_data['associations']
            )

        return {"classes": classes_data}

    def _extract_class_info(self, class_node: ast.ClassDef) -> Dict[str, Any]:
        """استخراج معلومات مفصلة عن الفئة"""
        class_name = class_node.name
        methods = []
        attributes = []
        associations = []

        base_classes = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_full_name(base))

        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._extract_method_info(item)
                methods.append(method_info['signature'])
                
                associations.extend(method_info['associations'])
                
                if item.name == '__init__':
                    init_analysis = self._analyze_init_method(item)
                    attributes.extend(init_analysis['attributes'])
                    associations.extend(init_analysis['associations'])
            
            elif isinstance(item, ast.Assign):
                attr_info = self._extract_class_attribute(item)
                if attr_info:
                    attributes.append(attr_info)

        return {
            "name": class_name,
            "methods": methods,
            "inherits": base_classes if base_classes else None,
            "attributes": attributes,
            "associations": associations
        }

    def _extract_method_info(self, method_node: ast.FunctionDef) -> Dict[str, Any]:
        """استخراج معلومات مفصلة عن الطريقة"""
        args = []
        associations = []
        
        for arg in method_node.args.args:
            if arg.arg != 'self':
                arg_type = self._get_type_annotation(arg)
                args.append(f"{arg.arg}: {arg_type}" if arg_type else arg.arg)
                
                if arg_type and self._is_class_type(arg_type):
                    associations.append({
                        "target_class": arg_type,
                        "type": "Association",
                        "attribute": arg.arg,
                        "source": f"method_{method_node.name}_parameter"
                    })

        signature = f"{method_node.name}({', '.join(args)})"
        
        if method_node.returns:
            return_type = self._get_annotation_name(method_node.returns)
            signature += f" -> {return_type}"

        return {
            "signature": signature,
            "associations": associations
        }

    def _analyze_init_method(self, init_node: ast.FunctionDef) -> Dict[str, Any]:
        """تحليل متقدم لطريقة __init__"""
        attributes = []
        associations = []
        
        for node in ast.walk(init_node):
            if isinstance(node, ast.Assign):
                if (len(node.targets) == 1 and 
                    isinstance(node.targets[0], ast.Attribute) and
                    isinstance(node.targets[0].value, ast.Name) and 
                    node.targets[0].value.id == 'self'):
                    
                    attr_name = node.targets[0].attr
                    attr_analysis = self._analyze_attribute_assignment(node.value, attr_name)
                    
                    attributes.append({
                        "name": attr_name,
                        "type": attr_analysis['type'],
                        "visibility": "private"
                    })
                    
                    if attr_analysis['association']:
                        associations.append(attr_analysis['association'])
                
                elif (len(node.targets) == 1 and 
                      isinstance(node.targets[0], ast.Name)):
                    pass

        return {
            "attributes": attributes,
            "associations": associations
        }

    def _analyze_attribute_assignment(self, value_node: ast.AST, attr_name: str) -> Dict[str, Any]:
        """تحليل تعيين الخاصية لتحديد النوع والعلاقة"""
        attr_type = "Any"
        association = None
        
        if isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                class_name = value_node.func.id
                if self._is_class_type(class_name):
                    attr_type = class_name
                    association = {
                        "target_class": class_name,
                        "type": "Composition",
                        "attribute": attr_name,
                        "source": "init_constructor_call"
                    }
        
        elif isinstance(value_node, ast.Name):
            var_name = value_node.id
            if self._is_parameter_name(var_name):
                association = {
                    "target_class": "Unknown",  # سيتم تحديده لاحقاً
                    "type": "Aggregation", 
                    "attribute": attr_name,
                    "source": "init_parameter_assignment"
                }
        
        elif isinstance(value_node, (ast.Str, ast.Constant)) and isinstance(getattr(value_node, 'value', value_node.s if hasattr(value_node, 's') else None), str):
            attr_type = "str"
        elif isinstance(value_node, (ast.Num, ast.Constant)) and isinstance(getattr(value_node, 'value', value_node.n if hasattr(value_node, 'n') else None), (int, float)):
            val = getattr(value_node, 'value', value_node.n if hasattr(value_node, 'n') else 0)
            attr_type = "int" if isinstance(val, int) else "float"
        elif isinstance(value_node, ast.List):
            attr_type = "List"
        elif isinstance(value_node, ast.Dict):
            attr_type = "Dict"
        elif isinstance(value_node, ast.Attribute):
            attr_type = "Any"

        return {
            "type": attr_type,
            "association": association
        }

    def _extract_class_attribute(self, assign_node: ast.Assign) -> Dict[str, Any]:
        """استخراج خاصية على مستوى الفئة"""
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                attr_name = target.id
                attr_type = self._infer_type_from_value(assign_node.value)
                
                return {
                    "name": attr_name,
                    "type": attr_type,
                    "visibility": "public"
                }
        return None

    def _deduplicate_associations(self, associations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """إزالة تكرار العلاقات"""
        seen = set()
        unique_associations = []
        
        for assoc in associations:
            key = (assoc['target_class'], assoc['type'], assoc['attribute'])
            if key not in seen:
                seen.add(key)
                unique_associations.append(assoc)
        
        logger.info(f"Deduplicated associations: {len(associations)} -> {len(unique_associations)}")
        return unique_associations
    def generate_dependency_graph_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """توليد بيانات فعلية لمخطط التبعيات"""
        logger.info("Generating enhanced dependency graph data...")
        tree = ast_data.get("ast_tree")
        if not tree:
            return {"nodes": [], "edges": []}

        if not hasattr(self, 'dependencies') or not self.dependencies:
            self.visitor.reset()
            self.visitor.visit(tree)
            self.dependencies = self.visitor.dependencies.copy()
            self.imports_map = self.visitor.imports_map.copy()
            self.classes_map = self.visitor.classes_map.copy()

        nodes = []
        edges = []
        
        for class_name in self.classes_map.keys():
            nodes.append({
                "id": class_name,
                "label": class_name,
                "type": "class",
                "local": True
            })

        for dependency in self.dependencies:
            if dependency not in [n["id"] for n in nodes]:  # تجنب التكرار
                nodes.append({
                    "id": dependency,
                    "label": dependency,
                    "type": "module", 
                    "local": False
                })

        for class_name, class_info in self.classes_map.items():
            if class_info.get('base_classes'):
                for base_class in class_info['base_classes']:
                    edges.append({
                        "source": class_name,
                        "target": base_class,
                        "type": "inheritance"
                    })

            for assoc in class_info.get('associations', []):
                edges.append({
                    "source": class_name,
                    "target": assoc['target_class'],
                    "type": assoc['type'].lower(),
                    "label": assoc['attribute']
                })

        for class_name in self.classes_map.keys():
            for dependency in self.dependencies:
                edges.append({
                    "source": class_name,
                    "target": dependency,
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

    def _get_type_annotation(self, arg: ast.arg) -> str:
        """استخراج نوع البيانات من annotation"""
        if hasattr(arg, 'annotation') and arg.annotation:
            return self._get_annotation_name(arg.annotation)
        return None

    def _get_annotation_name(self, annotation: ast.AST) -> str:
        """تحويل annotation إلى اسم نوع"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return self._get_full_name(annotation)
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        return "Any"

    def _get_full_name(self, attr_node: ast.Attribute) -> str:
        """الحصول على الاسم الكامل من ast.Attribute"""
        parts = []
        current = attr_node
        
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
            
        if isinstance(current, ast.Name):
            parts.append(current.id)
            
        return '.'.join(reversed(parts))

    def _is_class_type(self, type_name: str) -> bool:
        """تحديد ما إذا كان الاسم يمثل فئة"""
        return type_name and type_name[0].isupper()

    def _is_parameter_name(self, var_name: str) -> bool:
        """تحديد ما إذا كان الاسم parameter في دالة"""
        return var_name != 'self'

    def _infer_type_from_value(self, value_node: ast.AST) -> str:
        """استنتاج نوع البيانات من القيمة"""
        if isinstance(value_node, ast.Str):
            return "str"
        elif isinstance(value_node, ast.Num):
            return "int" if isinstance(value_node.n, int) else "float"
        elif isinstance(value_node, ast.List):
            return "List"
        elif isinstance(value_node, ast.Dict):
            return "Dict"
        elif isinstance(value_node, ast.Call):
            if isinstance(value_node.func, ast.Name):
                return value_node.func.id
        return "Any"     