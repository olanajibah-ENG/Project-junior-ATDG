"""
Advanced AST Analyzer - محلل AST متقدم باستخدام NodeVisitor
===========================================================

هذا المحلل يحل المشاكل التالية:
1. عد الدوال الخاطئ باستخدام ast.NodeVisitor
2. استخراج العلاقات الدقيق (Composition, Aggregation, Dependency)
3. تحليل dependency_graph فعال
4. استخراج الخصائص من __init__
5. إزالة التكرار في associations

المؤلف: Kiro AI Assistant
التاريخ: 2025-12-28
"""

import ast
import logging
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class AdvancedASTAnalyzer(ast.NodeVisitor):
    """محلل AST متقدم باستخدام NodeVisitor لضمان الدقة"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """إعادة تعيين جميع البيانات"""
        self.function_definitions = []  # تعريفات الدوال فقط
        self.method_definitions = []    # تعريفات الطرق فقط
        self.class_definitions = []     # تعريفات الفئات
        
        self.classes_map = {}           # {class_name: class_info}
        self.imports_map = {}           # {alias: module_name}
        self.dependencies = set()       # التبعيات الخارجية
        
        self.current_class = None       # الفئة الحالية
        self.current_method = None      # الطريقة الحالية
        self.in_class_context = False   # هل نحن داخل فئة؟
        
        self.relationships = defaultdict(list)  # {class_name: [relationships]}
        
        self.stats = {
            'total_nodes_visited': 0,
            'function_calls_ignored': 0,
            'imports_processed': 0
        }
    
    def analyze_code(self, code_content: str) -> Dict[str, Any]:
        """تحليل الكود الرئيسي"""
        logger.info("Starting advanced AST analysis with NodeVisitor...")
        
        try:
            tree = ast.parse(code_content)
            
            self.reset()
            
            self.visit(tree)
            
            results = self._build_results(code_content)
            
            logger.info(f"Analysis completed. Stats: {self.stats}")
            return results
            
        except SyntaxError as e:
            logger.error(f"Syntax error in code: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {"error": str(e)}
    
    def visit(self, node):
        """زيارة العقدة مع تتبع الإحصائيات"""
        self.stats['total_nodes_visited'] += 1
        super().visit(node)
    
    def visit_Import(self, node):
        """معالجة import statements"""
        self.stats['imports_processed'] += 1
        
        for alias in node.names:
            module_name = alias.name
            alias_name = alias.asname or alias.name
            
            root_module = module_name.split('.')[0]
            self.dependencies.add(root_module)
            
            self.imports_map[alias_name] = module_name
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """معالجة from ... import statements"""
        self.stats['imports_processed'] += 1
        
        if node.module:
            root_module = node.module.split('.')[0]
            self.dependencies.add(root_module)
            
            for alias in node.names:
                imported_name = alias.name
                alias_name = alias.asname or alias.name
                full_name = f"{node.module}.{imported_name}"
                self.imports_map[alias_name] = full_name
        
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
            'base_classes': self._extract_base_classes(node),
            'associations': []
        }
        
        self.class_definitions.append(class_info)
        self.classes_map[node.name] = class_info
        
        self.generic_visit(node)
        
        self.current_class = old_class
        self.in_class_context = old_in_class
    
    def visit_FunctionDef(self, node):
        """معالجة تعريفات الدوال والطرق"""
        old_method = self.current_method
        self.current_method = node.name
        
        function_info = {
            'name': node.name,
            'line': node.lineno,
            'is_async': False,
            'parameters': [arg.arg for arg in node.args.args],
            'return_annotation': self._get_return_annotation(node)
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
            function_info['class_name'] = None
            self.function_definitions.append(function_info)
        
        self.generic_visit(node)
        
        self.current_method = old_method
    
    def visit_AsyncFunctionDef(self, node):
        """معالجة الدوال غير المتزامنة"""
        old_method = self.current_method
        self.current_method = node.name
        
        function_info = {
            'name': node.name,
            'line': node.lineno,
            'is_async': True,
            'parameters': [arg.arg for arg in node.args.args],
            'return_annotation': self._get_return_annotation(node)
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
            function_info['class_name'] = None
            self.function_definitions.append(function_info)
        
        self.generic_visit(node)
        self.current_method = old_method
    
    def visit_Call(self, node):
        """معالجة استدعاءات الدوال - نتجاهلها في العد"""
        self.stats['function_calls_ignored'] += 1
        self.generic_visit(node)
    
    def _extract_base_classes(self, class_node):
        """استخراج الفئات الأساسية للوراثة"""
        base_classes = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(self._get_full_name(base))
        return base_classes
    
    def _analyze_init_method(self, init_node):
        """تحليل متقدم لطريقة __init__"""
        if not self.current_class:
            return
        
        class_info = self.classes_map[self.current_class]
        
        for node in ast.walk(init_node):
            if isinstance(node, ast.Assign):
                self._analyze_assignment_in_init(node, class_info)
    
    def _analyze_assignment_in_init(self, assign_node, class_info):
        """تحليل التعيينات في __init__"""
        if (len(assign_node.targets) == 1 and 
            isinstance(assign_node.targets[0], ast.Attribute) and
            isinstance(assign_node.targets[0].value, ast.Name) and 
            assign_node.targets[0].value.id == 'self'):
            
            attr_name = assign_node.targets[0].attr
            attr_type, relationship = self._analyze_attribute_value(assign_node.value, attr_name)
            
            attribute = {
                'name': attr_name,
                'type': attr_type,
                'visibility': 'private'
            }
            class_info['attributes'].append(attribute)
            
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
                attr_type = "Parameter"
                relationship = {
                    'target_class': 'Unknown',
                    'type': 'Aggregation',
                    'attribute': attr_name,
                    'source': 'init_parameter_assignment'
                }
        
        elif isinstance(value_node, (ast.Str, ast.Constant)):
            if hasattr(value_node, 'value'):
                if isinstance(value_node.value, str):
                    attr_type = "str"
            elif hasattr(value_node, 's'):
                attr_type = "str"
        
        elif isinstance(value_node, (ast.Num, ast.Constant)):
            if hasattr(value_node, 'value'):
                attr_type = "int" if isinstance(value_node.value, int) else "float"
            elif hasattr(value_node, 'n'):
                attr_type = "int" if isinstance(value_node.n, int) else "float"
        
        elif isinstance(value_node, ast.List):
            attr_type = "List"
        elif isinstance(value_node, ast.Dict):
            attr_type = "Dict"
        
        return attr_type, relationship
    
    def _analyze_method_parameters(self, method_node):
        """تحليل parameters الطريقة للعلاقات"""
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
        
        return_type = self._get_return_annotation(method_node)
        if return_type:
            signature += f" -> {return_type}"
        
        return signature
    
    def _get_type_annotation(self, arg):
        """استخراج نوع البيانات من annotation"""
        if hasattr(arg, 'annotation') and arg.annotation:
            return self._get_annotation_name(arg.annotation)
        return None
    
    def _get_return_annotation(self, func_node):
        """استخراج نوع الإرجاع"""
        if hasattr(func_node, 'returns') and func_node.returns:
            return self._get_annotation_name(func_node.returns)
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
        """الحصول على الاسم الكامل من ast.Attribute"""
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
    
    def _deduplicate_associations(self, associations):
        """إزالة تكرار العلاقات"""
        seen = set()
        unique = []
        
        for assoc in associations:
            key = (assoc['target_class'], assoc['type'], assoc['attribute'])
            if key not in seen:
                seen.add(key)
                unique.append(assoc)
        
        return unique
    
    def _build_results(self, code_content):
        """بناء النتائج النهائية"""
        lines_of_code = len(code_content.splitlines())
        
        for class_info in self.classes_map.values():
            class_info['associations'] = self._deduplicate_associations(
                class_info['associations']
            )
        
        dependency_graph = self._build_dependency_graph()
        
        results = {
            'ast_structure': {
                'code_content': code_content
            },
            'extracted_features': {
                'lines_of_code': lines_of_code,
                'functions': len(self.function_definitions) + len(self.method_definitions),
                'standalone_functions': len(self.function_definitions),
                'methods': len(self.method_definitions),
                'classes': len(self.class_definitions),
                'function_details': self.function_definitions + self.method_definitions
            },
            'dependencies': list(self.dependencies),
            'dependency_graph': dependency_graph,
            'semantic_analysis_data': {
                'issues': self._find_semantic_issues(),
                'abstract_classes': self._find_abstract_classes(),
                'imports_analysis': self.imports_map
            },
            'class_diagram_data': {
                'classes': list(self.classes_map.values())
            },
            'analysis_stats': self.stats
        }
        
        return results
    
    def _build_dependency_graph(self):
        """بناء مخطط التبعيات"""
        nodes = []
        edges = []
        
        for class_name in self.classes_map.keys():
            nodes.append({
                'id': class_name,
                'label': class_name,
                'type': 'class',
                'local': True
            })
        
        for module_name in self.dependencies:
            nodes.append({
                'id': module_name,
                'label': module_name,
                'type': 'module',
                'local': False
            })
        
        for class_name, class_info in self.classes_map.items():
            if class_info.get('base_classes'):
                for base_class in class_info['base_classes']:
                    edges.append({
                        'source': class_name,
                        'target': base_class,
                        'type': 'inheritance'
                    })
        
        for class_name, class_info in self.classes_map.items():
            for assoc in class_info.get('associations', []):
                edges.append({
                    'source': class_name,
                    'target': assoc['target_class'],
                    'type': assoc['type'].lower(),
                    'label': assoc['attribute']
                })
        
        for class_name in self.classes_map.keys():
            for module_name in self.dependencies:
                edges.append({
                    'source': class_name,
                    'target': module_name,
                    'type': 'dependency'
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'local_classes': len([n for n in nodes if n.get('local', False)]),
                'external_modules': len([n for n in nodes if not n.get('local', True)])
            }
        }
    
    def _find_semantic_issues(self):
        """البحث عن المشاكل الدلالية"""
        issues = []
        
        if 'requests' in self.dependencies:
            issues.append({
                'type': 'info',
                'message': 'External dependency detected: requests',
                'category': 'dependency'
            })
        
        return issues
    
    def _find_abstract_classes(self):
        """البحث عن الفئات التجريدية"""
        abstract_classes = []
        
        for class_info in self.classes_map.values():
            if 'ABC' in class_info.get('base_classes', []):
                abstract_classes.append(class_info['name'])
        
        return abstract_classes


def create_enhanced_python_processor():
    """إنشاء معالج Python محسن باستخدام AdvancedASTAnalyzer"""
    
    class EnhancedPythonProcessor:
        def __init__(self):
            self.analyzer = AdvancedASTAnalyzer()
        
        def parse_source_code(self, code_content: str) -> Dict[str, Any]:
            return {"ast_tree": "processed", "code_content": code_content}
        
        def extract_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
            code_content = ast_data.get("code_content", "")
            results = self.analyzer.analyze_code(code_content)
            return results.get('extracted_features', {})
        
        def extract_dependencies(self, ast_data: Dict[str, Any]) -> List[str]:
            code_content = ast_data.get("code_content", "")
            results = self.analyzer.analyze_code(code_content)
            return results.get('dependencies', [])
        
        def perform_semantic_analysis(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
            code_content = ast_data.get("code_content", "")
            results = self.analyzer.analyze_code(code_content)
            return results.get('semantic_analysis_data', {})
        
        def generate_class_diagram_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
            code_content = ast_data.get("code_content", "")
            results = self.analyzer.analyze_code(code_content)
            return results.get('class_diagram_data', {})
        
        def generate_dependency_graph_data(self, ast_data: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
            code_content = ast_data.get("code_content", "")
            results = self.analyzer.analyze_code(code_content)
            return results.get('dependency_graph', {})
    
    return EnhancedPythonProcessor()