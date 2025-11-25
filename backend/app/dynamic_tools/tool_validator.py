"""
Dynamic Tool Validator - Ensures safe execution of LLM-generated Python code.
Validates code against security rules before allowing execution.
"""
import ast
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DynamicToolValidator:
    """
    Validates LLM-generated Python code for safety before execution.

    Security Rules:
    1. No imports outside whitelist
    2. No file I/O operations
    3. No network access
    4. No subprocess/system calls
    5. Pure deterministic logic only
    6. Limited built-ins access
    """

    # Whitelist of allowed imports
    ALLOWED_IMPORTS = {
        "math", "statistics", "datetime", "decimal", "re", "json",
        "typing", "collections", "itertools", "functools"
    }

    # Forbidden built-ins
    FORBIDDEN_BUILTINS = {
        "open", "eval", "exec", "compile", "__import__",
        "input", "raw_input", "file", "execfile",
        "reload", "vars", "dir", "globals", "locals"
    }

    # Forbidden AST node types
    FORBIDDEN_NODES = {
        ast.Import: "Direct imports not allowed",
        ast.ImportFrom: "Import from statements not allowed",
        ast.With: "Context managers (with) not allowed",
        ast.AsyncFunctionDef: "Async functions not allowed",
        ast.AsyncFor: "Async for loops not allowed",
        ast.AsyncWith: "Async with not allowed",
        ast.Global: "Global variable modification not allowed",
        ast.Nonlocal: "Nonlocal variable modification not allowed",
    }

    def __init__(self):
        self.validation_errors: List[str] = []

    def validate(self, code: str, function_name: str) -> Dict[str, Any]:
        """
        Validate Python code for safety.

        Args:
            code: Python source code string
            function_name: Expected function name

        Returns:
            dict with keys: valid (bool), errors (list), ast_tree (optional)
        """
        self.validation_errors = []

        # Step 1: Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.validation_errors.append(f"Syntax error: {e}")
            return {"valid": False, "errors": self.validation_errors}

        # Step 2: Validate function exists
        function_def = self._find_function_def(tree, function_name)
        if not function_def:
            self.validation_errors.append(f"Function '{function_name}' not found in code")
            return {"valid": False, "errors": self.validation_errors}

        # Step 3: Check for forbidden operations
        self._validate_ast_tree(tree)

        # Step 4: Check for imports
        self._validate_imports(tree)

        # Step 5: Check for forbidden built-ins
        self._validate_builtins(tree)

        # Step 6: Check for file I/O
        self._validate_no_file_io(tree)

        # Step 7: Check for network access
        self._validate_no_network(tree)

        if self.validation_errors:
            return {
                "valid": False,
                "errors": self.validation_errors,
            }

        return {
            "valid": True,
            "errors": [],
            "ast_tree": tree,
            "function_def": function_def,
        }

    def _find_function_def(self, tree: ast.AST, function_name: str) -> Optional[ast.FunctionDef]:
        """Find function definition in AST"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return node
        return None

    def _validate_ast_tree(self, tree: ast.AST):
        """Check for forbidden AST node types"""
        for node in ast.walk(tree):
            node_type = type(node)
            if node_type in self.FORBIDDEN_NODES:
                reason = self.FORBIDDEN_NODES[node_type]
                self.validation_errors.append(f"Forbidden operation: {reason}")

    def _validate_imports(self, tree: ast.AST):
        """Validate that only whitelisted imports are used"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Extract module names
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.ALLOWED_IMPORTS:
                            self.validation_errors.append(
                                f"Import '{alias.name}' not allowed. Allowed: {', '.join(self.ALLOWED_IMPORTS)}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module not in self.ALLOWED_IMPORTS:
                        self.validation_errors.append(
                            f"Import from '{node.module}' not allowed. Allowed: {', '.join(self.ALLOWED_IMPORTS)}"
                        )

    def _validate_builtins(self, tree: ast.AST):
        """Check for forbidden built-in function usage"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in self.FORBIDDEN_BUILTINS:
                self.validation_errors.append(
                    f"Forbidden built-in function: {node.id}"
                )

    def _validate_no_file_io(self, tree: ast.AST):
        """Check for file I/O operations"""
        file_io_keywords = {"open", "file", "read", "write", "os.path", "Path"}

        for node in ast.walk(tree):
            # Check for direct file operations
            if isinstance(node, ast.Name) and node.id in {"open", "file"}:
                self.validation_errors.append(
                    f"File I/O operation not allowed: {node.id}"
                )

            # Check for attribute access (e.g., os.path)
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "os":
                    self.validation_errors.append(
                        "OS module access not allowed (file system operations)"
                    )

    def _validate_no_network(self, tree: ast.AST):
        """Check for network operations"""
        network_keywords = {
            "urllib", "requests", "http", "socket",
            "httpx", "aiohttp", "websocket"
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in network_keywords:
                self.validation_errors.append(
                    f"Network operation not allowed: {node.id}"
                )

    def extract_function_metadata(self, function_def: ast.FunctionDef) -> Dict[str, Any]:
        """
        Extract metadata from function definition.

        Returns:
            dict with: name, args, returns, docstring
        """
        # Extract arguments
        args = []
        for arg in function_def.args.args:
            arg_name = arg.arg
            arg_type = None
            if arg.annotation:
                arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            args.append({"name": arg_name, "type": arg_type})

        # Extract return type
        return_type = None
        if function_def.returns:
            return_type = ast.unparse(function_def.returns) if hasattr(ast, 'unparse') else str(function_def.returns)

        # Extract docstring
        docstring = ast.get_docstring(function_def)

        return {
            "name": function_def.name,
            "args": args,
            "returns": return_type,
            "docstring": docstring or "No description provided",
        }
