"""Python AST parser for extracting code entities and relationships."""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config.logging_config import get_logger
from core.exceptions import ParsingError
from core.types import EntityType, RelationshipType

logger = get_logger(__name__)


class EntityInfo:
    """Represents extracted information about a code entity."""

    def __init__(
        self,
        entity_type: EntityType,
        name: str,
        line_number: int,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.entity_type = entity_type
        self.name = name
        self.line_number = line_number
        self.properties = properties or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_type": self.entity_type.value,
            "name": self.name,
            "line_number": self.line_number,
            **self.properties,
        }


class RelationshipInfo:
    """Represents a relationship between two entities."""

    def __init__(
        self,
        rel_type: RelationshipType,
        source: str,
        target: str,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.rel_type = rel_type
        self.source = source
        self.target = target
        self.properties = properties or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rel_type": self.rel_type.value,
            "source": self.source,
            "target": self.target,
            **self.properties,
        }


class PythonASTParser:
    """Parser for extracting entities and relationships from Python AST."""

    def __init__(self, file_path: str, module_path: str):
        """Initialize parser.
        
        Args:
            file_path: Path to the Python file.
            module_path: Module path (e.g., 'fastapi.routing').
        """
        self.file_path = file_path
        self.module_path = module_path
        self.entities: List[EntityInfo] = []
        self.relationships: List[RelationshipInfo] = []

    def parse_file(self) -> Tuple[List[EntityInfo], List[RelationshipInfo]]:
        """Parse the Python file and extract entities and relationships.
        
        Returns:
            Tuple of (entities, relationships).
            
        Raises:
            ParsingError: If parsing fails.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse AST
            tree = ast.parse(source_code, filename=self.file_path)
            
            # Extract module-level information
            module_docstring = ast.get_docstring(tree)
            self.entities.append(
                EntityInfo(
                    EntityType.MODULE,
                    self.module_path,
                    1,
                    {
                        "path": self.module_path,
                        "file_path": self.file_path,
                        "docstring": module_docstring or "",
                    },
                )
            )
            
            # Walk the AST
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._parse_class(node)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    # Only parse top-level functions (methods are handled in _parse_class)
                    if self._is_top_level(node, tree):
                        self._parse_function(node, is_method=False)
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    self._parse_import(node)
            
            logger.debug(
                f"Parsed {self.file_path}: {len(self.entities)} entities, "
                f"{len(self.relationships)} relationships"
            )
            
            return self.entities, self.relationships
            
        except SyntaxError as e:
            raise ParsingError(f"Syntax error: {e}", file_path=self.file_path)
        except Exception as e:
            raise ParsingError(f"Failed to parse file: {e}", file_path=self.file_path)

    def _is_top_level(self, node: ast.AST, tree: ast.Module) -> bool:
        """Check if a node is at the top level of the module."""
        return node in tree.body

    def _parse_class(self, node: ast.ClassDef) -> None:
        """Parse a class definition."""
        class_name = f"{self.module_path}.{node.name}"
        docstring = ast.get_docstring(node) or ""
        
        # Determine if class is abstract
        is_abstract = any(
            isinstance(d, ast.Name) and d.id == "ABC"
            for d in node.bases
        )
        
        # Add class entity
        self.entities.append(
            EntityInfo(
                EntityType.CLASS,
                class_name,
                node.lineno,
                {
                    "name": node.name,
                    "module_path": self.module_path,
                    "docstring": docstring,
                    "is_abstract": is_abstract,
                },
            )
        )
        
        # Add CONTAINS relationship from module to class
        self.relationships.append(
            RelationshipInfo(
                RelationshipType.CONTAINS,
                self.module_path,
                class_name,
            )
        )
        
        # Parse base classes (inheritance)
        for base in node.bases:
            base_name = self._get_name_from_node(base)
            if base_name and base_name != "ABC":
                self.relationships.append(
                    RelationshipInfo(
                        RelationshipType.INHERITS_FROM,
                        class_name,
                        base_name,
                    )
                )
        
        # Parse decorators
        for decorator in node.decorator_list:
            decorator_name = self._get_name_from_node(decorator)
            if decorator_name:
                self._add_decorator(class_name, decorator_name)
        
        # Parse methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._parse_function(item, is_method=True, parent_class=class_name)
        
        # Parse docstring as separate entity
        if docstring:
            self._add_docstring(class_name, docstring, node.lineno)

    def _parse_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_method: bool = False,
        parent_class: Optional[str] = None,
    ) -> None:
        """Parse a function or method definition."""
        if is_method:
            entity_type = EntityType.METHOD
            full_name = f"{parent_class}.{node.name}"
        else:
            entity_type = EntityType.FUNCTION
            full_name = f"{self.module_path}.{node.name}"
        
        docstring = ast.get_docstring(node) or ""
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        # Get function signature
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"
        
        # Check if static or classmethod
        is_static = False
        is_classmethod = False
        if is_method:
            for decorator in node.decorator_list:
                dec_name = self._get_name_from_node(decorator)
                if dec_name == "staticmethod":
                    is_static = True
                elif dec_name == "classmethod":
                    is_classmethod = True
        
        # Add function/method entity
        properties = {
            "name": node.name,
            "module_path": self.module_path,
            "docstring": docstring,
            "is_async": is_async,
            "signature": signature,
        }
        
        if is_method:
            properties["is_static"] = is_static
            properties["is_classmethod"] = is_classmethod
        
        self.entities.append(
            EntityInfo(entity_type, full_name, node.lineno, properties)
        )
        
        # Add CONTAINS relationship
        parent = parent_class if is_method else self.module_path
        self.relationships.append(
            RelationshipInfo(RelationshipType.CONTAINS, parent, full_name)
        )
        
        # Parse parameters
        for i, arg in enumerate(node.args.args):
            self._add_parameter(full_name, arg, i)
        
        # Parse decorators
        for decorator in node.decorator_list:
            decorator_name = self._get_name_from_node(decorator)
            if decorator_name and decorator_name not in ["staticmethod", "classmethod"]:
                self._add_decorator(full_name, decorator_name)
        
        # Parse docstring
        if docstring:
            self._add_docstring(full_name, docstring, node.lineno)

    def _parse_import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Parse import statement."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_name = f"{self.module_path}.import.{alias.name}"
                self.entities.append(
                    EntityInfo(
                        EntityType.IMPORT,
                        import_name,
                        node.lineno,
                        {
                            "module_name": alias.name,
                            "imported_names": [alias.name],
                            "is_from_import": False,
                        },
                    )
                )
                
                self.relationships.append(
                    RelationshipInfo(
                        RelationshipType.IMPORTS,
                        self.module_path,
                        alias.name,
                    )
                )
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = [alias.name for alias in node.names]
            
            import_name = f"{self.module_path}.import.{module}"
            self.entities.append(
                EntityInfo(
                    EntityType.IMPORT,
                    import_name,
                    node.lineno,
                    {
                        "module_name": module,
                        "imported_names": imported_names,
                        "is_from_import": True,
                    },
                )
            )
            
            if module:
                self.relationships.append(
                    RelationshipInfo(
                        RelationshipType.IMPORTS,
                        self.module_path,
                        module,
                    )
                )

    def _add_parameter(self, parent: str, arg: ast.arg, position: int) -> None:
        """Add a parameter entity."""
        param_name = f"{parent}.param.{arg.arg}"
        type_annotation = ast.unparse(arg.annotation) if arg.annotation else None
        
        self.entities.append(
            EntityInfo(
                EntityType.PARAMETER,
                param_name,
                arg.lineno,
                {
                    "name": arg.arg,
                    "type_annotation": type_annotation,
                    "position": position,
                },
            )
        )
        
        self.relationships.append(
            RelationshipInfo(RelationshipType.HAS_PARAMETER, parent, param_name)
        )

    def _add_decorator(self, parent: str, decorator_name: str) -> None:
        """Add a decorator entity."""
        dec_name = f"{parent}.decorator.{decorator_name}"
        
        self.entities.append(
            EntityInfo(
                EntityType.DECORATOR,
                dec_name,
                0,
                {"name": decorator_name},
            )
        )
        
        self.relationships.append(
            RelationshipInfo(RelationshipType.DECORATED_BY, parent, decorator_name)
        )

    def _add_docstring(self, parent: str, content: str, line_number: int) -> None:
        """Add a docstring entity."""
        doc_name = f"{parent}.docstring"
        
        self.entities.append(
            EntityInfo(
                EntityType.DOCSTRING,
                doc_name,
                line_number,
                {"content": content},
            )
        )
        
        self.relationships.append(
            RelationshipInfo(RelationshipType.DOCUMENTED_BY, parent, doc_name)
        )

    def _get_name_from_node(self, node: ast.AST) -> Optional[str]:
        """Extract name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # For things like @dataclass or fastapi.Depends
            try:
                return ast.unparse(node)
            except:
                return None
        elif isinstance(node, ast.Call):
            # For decorator calls like @app.get("/")
            return self._get_name_from_node(node.func)
        return None
