"""Code analysis utilities for understanding code structure and complexity."""

import ast
from typing import Any, Dict, List, Set

from config.logging_config import get_logger

logger = get_logger(__name__)


class CodeAnalyzer:
    """Analyzer for Python code structure and complexity."""

    @staticmethod
    def analyze_function_complexity(code: str) -> Dict[str, Any]:
        """Analyze function complexity metrics.
        
        Args:
            code: Function source code.
            
        Returns:
            Dictionary with complexity metrics.
        """
        try:
            tree = ast.parse(code)
            
            # Find function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_def = node
                    break
            
            if not func_def:
                return {"error": "No function definition found"}
            
            # Calculate metrics
            metrics = {
                "name": func_def.name,
                "is_async": isinstance(func_def, ast.AsyncFunctionDef),
                "line_count": len(code.split('\n')),
                "cyclomatic_complexity": CodeAnalyzer._calculate_complexity(func_def),
                "parameter_count": len(func_def.args.args),
                "has_docstring": ast.get_docstring(func_def) is not None,
                "has_return_annotation": func_def.returns is not None,
                "decorators": [
                    ast.unparse(d) if hasattr(ast, 'unparse') else str(d)
                    for d in func_def.decorator_list
                ],
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Function complexity analysis failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def _calculate_complexity(node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node.
        
        Args:
            node: AST node to analyze.
            
        Returns:
            Cyclomatic complexity score.
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity

    @staticmethod
    def analyze_class_structure(code: str) -> Dict[str, Any]:
        """Analyze class structure and characteristics.
        
        Args:
            code: Class source code.
            
        Returns:
            Dictionary with class analysis.
        """
        try:
            tree = ast.parse(code)
            
            # Find class definition
            class_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_def = node
                    break
            
            if not class_def:
                return {"error": "No class definition found"}
            
            # Analyze methods
            methods = []
            properties = []
            
            for item in class_def.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_info = {
                        "name": item.name,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "is_private": item.name.startswith('_'),
                        "is_magic": item.name.startswith('__') and item.name.endswith('__'),
                    }
                    
                    # Check for decorators
                    for decorator in item.decorator_list:
                        dec_name = (
                            decorator.id if isinstance(decorator, ast.Name)
                            else ast.unparse(decorator) if hasattr(ast, 'unparse')
                            else str(decorator)
                        )
                        
                        if dec_name == "property":
                            properties.append(method_info)
                            break
                    else:
                        methods.append(method_info)
            
            analysis = {
                "name": class_def.name,
                "has_docstring": ast.get_docstring(class_def) is not None,
                "base_classes": [
                    ast.unparse(base) if hasattr(ast, 'unparse') else str(base)
                    for base in class_def.bases
                ],
                "decorators": [
                    ast.unparse(d) if hasattr(ast, 'unparse') else str(d)
                    for d in class_def.decorator_list
                ],
                "method_count": len(methods),
                "property_count": len(properties),
                "methods": methods,
                "properties": properties,
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Class structure analysis failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def extract_function_calls(code: str) -> List[str]:
        """Extract all function calls from code.
        
        Args:
            code: Source code to analyze.
            
        Returns:
            List of function names called.
        """
        try:
            tree = ast.parse(code)
            calls = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        # For method calls like obj.method()
                        if hasattr(ast, 'unparse'):
                            calls.add(ast.unparse(node.func))
            
            return sorted(list(calls))
            
        except Exception as e:
            logger.error(f"Function call extraction failed: {e}")
            return []

    @staticmethod
    def identify_imports(code: str) -> Dict[str, List[str]]:
        """Identify all imports in code.
        
        Args:
            code: Source code to analyze.
            
        Returns:
            Dictionary with import and from-import lists.
        """
        try:
            tree = ast.parse(code)
            imports = []
            from_imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    items = [alias.name for alias in node.names]
                    from_imports.append(f"{module}: {', '.join(items)}")
            
            return {
                "imports": imports,
                "from_imports": from_imports,
            }
            
        except Exception as e:
            logger.error(f"Import identification failed: {e}")
            return {"imports": [], "from_imports": []}
