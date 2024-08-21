import ast
import json
from typing import List, Optional
from pydantic import BaseModel

class Alias(BaseModel):
    actual_name: str
    alias_name: str
    local_file: bool

class Node(BaseModel):
    type: str
    content: str
    children: List['Node'] = []
    function: Optional[str] = None
    alias: Optional[Alias] = None
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None

class PyFileAnalyzer(ast.NodeVisitor):
    def __init__(self, source_code):
        self.root = Node(type="module", content="", children=[])
        self.current_node = self.root
        self.source_code = source_code.splitlines()

    def get_node_content(self, node):
        start_line = node.lineno - 1
        end_line = node.end_lineno
        content = ' '.join(self.source_code[start_line:end_line]).strip()
        return content

    def visit_FunctionDef(self, node):
        content = self.get_node_content(node)
        func_node = Node(
            type="function",
            content=content,
            line_number=node.lineno,
            end_line_number=node.end_lineno,
            function=node.name
        )
        self.current_node.children.append(func_node)
        old_node = self.current_node
        self.current_node = func_node
        self.generic_visit(node)
        self.current_node = old_node

    def visit_ClassDef(self, node):
        content = self.get_node_content(node)
        class_node = Node(
            type="class",
            content=content,
            line_number=node.lineno,
            end_line_number=node.end_lineno
        )
        self.current_node.children.append(class_node)
        old_node = self.current_node
        self.current_node = class_node
        self.generic_visit(node)
        self.current_node = old_node

    def visit_Import(self, node):
        content = self.get_node_content(node)
        for alias in node.names:
            import_node = Node(
                type="import",
                content=content,
                line_number=node.lineno,
                alias=Alias(actual_name=alias.name, alias_name=alias.asname or alias.name, local_file=False)
            )
            self.current_node.children.append(import_node)

    def visit_ImportFrom(self, node):
        content = self.get_node_content(node)
        module = node.module or ""
        for alias in node.names:
            import_node = Node(
                type="import",
                content=content,
                line_number=node.lineno,
                alias=Alias(actual_name=f"{module}.{alias.name}", alias_name=alias.asname or alias.name, local_file=False)
            )
            self.current_node.children.append(import_node)

    def visit_Call(self, node):
        content = self.get_node_content(node)
        if isinstance(node.func, ast.Name):
            call_node = Node(
                type="function_call",
                content=content,
                line_number=node.lineno,
                function=node.func.id
            )
            self.current_node.children.append(call_node)
        elif isinstance(node.func, ast.Attribute):
            call_node = Node(
                type="function_call",
                content=content,
                line_number=node.lineno,
                function=self.get_full_attribute_name(node.func)
            )
            self.current_node.children.append(call_node)
        self.generic_visit(node)

    def get_full_attribute_name(self, node):
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self.get_full_attribute_name(node.value)}.{node.attr}"
        return node.attr

def analyze_python_file(file_path: str) -> Node:
    with open(file_path, "r") as file:
        source_code = file.read()
        tree = ast.parse(source_code, filename=file_path)
    
    analyzer = PyFileAnalyzer(source_code)
    analyzer.visit(tree)
    return analyzer.root

def node_to_dict(node: Node) -> dict:
    result = {
        "type": node.type,
        "content": node.content,
        "children": [node_to_dict(child) for child in node.children],
        "line_number": node.line_number,
        "end_line_number": node.end_line_number
    }
    if node.function:
        result["function"] = node.function
    if node.alias:
        result["alias"] = node.alias.dict()
    return result


# Example usage
file_path = "python file path"  # Replace with your actual Python file path
root_node = analyze_python_file(file_path)

# Convert to JSON
json_output = json.dumps(node_to_dict(root_node), indent=2)

# Save to file
with open("test_folder/output.json", "w") as json_file:
    json_file.write(json_output)

print("Analysis complete. Results saved to output.json")
