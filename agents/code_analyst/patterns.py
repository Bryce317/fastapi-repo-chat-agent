"""Design pattern detection utilities."""

import ast
import re
from typing import Dict, List, Set

from config.logging_config import get_logger

logger = get_logger(__name__)


class PatternDetector:
    """Detector for common design patterns in Python code."""

    @staticmethod
    def detect_patterns(code: str) -> Dict[str, List[str]]:
        """Detect design patterns in code.
        
        Args:
            code: Source code to analyze.
            
        Returns:
            Dictionary mapping pattern names to descriptions.
        """
        patterns = {}
        
        try:
            tree = ast.parse(code)
            
            # Detect singleton pattern
            if PatternDetector._is_singleton(tree):
                patterns["Singleton"] = ["Class implements singleton pattern with instance checking"]
            
            # Detect factory pattern
            factory_methods = PatternDetector._find_factory_methods(tree)
            if factory_methods:
                patterns["Factory"] = factory_methods
            
            # Detect decorator pattern
            if PatternDetector._has_decorator_pattern(tree):
                patterns["Decorator"] = ["Uses Python decorators for extending behavior"]
            
            # Detect context manager pattern
            if PatternDetector._is_context_manager(tree):
                patterns["Context Manager"] = ["Implements __enter__ and __exit__ methods"]
            
            # Detect property pattern
            properties = PatternDetector._find_properties(tree)
            if properties:
                patterns["Property"] = properties
            
            # Detect observer pattern (basic heuristic)
            if PatternDetector._has_observer_pattern(tree):
                patterns["Observer"] = ["Implements observer/subscriber pattern"]
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
        
        return patterns

    @staticmethod
    def _is_singleton(tree: ast.AST) -> bool:
        """Check if code implements singleton pattern."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Look for _instance or instance class variable
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id in ['_instance', 'instance', '_instances']:
                                    return True
        return False

    @staticmethod
    def _find_factory_methods(tree: ast.AST) -> List[str]:
        """Find factory methods in code."""
        factory_methods = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for factory naming patterns
                if any(pattern in node.name.lower() for pattern in ['create', 'factory', 'build', 'make']):
                    factory_methods.append(f"Method '{node.name}' appears to be a factory method")
        
        return factory_methods

    @staticmethod
    def _has_decorator_pattern(tree: ast.AST) -> bool:
        """Check if code uses decorator pattern."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.decorator_list:
                    return True
        return False

    @staticmethod
    def _is_context_manager(tree: ast.AST) -> bool:
        """Check if class implements context manager protocol."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = {
                    item.name 
                    for item in node.body 
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                
                if '__enter__' in methods and '__exit__' in methods:
                    return True
                
                if '__aenter__' in methods and '__aexit__' in methods:
                    return True
        
        return False

    @staticmethod
    def _find_properties(tree: ast.AST) -> List[str]:
        """Find properties in code."""
        properties = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'property':
                        properties.append(f"Property '{node.name}'")
        
        return properties

    @staticmethod
    def _has_observer_pattern(tree: ast.AST) -> bool:
        """Check for observer pattern characteristics."""
        # Look for subscribe/unsubscribe or add_listener/remove_listener methods
        observer_keywords = [
            'subscribe', 'unsubscribe', 'notify', 'observer',
            'listener', 'add_listener', 'remove_listener', 'emit'
        ]
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(keyword in node.name.lower() for keyword in observer_keywords):
                    return True
        
        return False
