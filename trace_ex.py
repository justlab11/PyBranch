import json
import re
from typing import *
import os
import glob
from custom_types import *


def get_alias(node: Node, folder: str):
    filename = node.content.split(" ")[1]
    filename = filename.replace(".", "/")

    file_loc = os.path.join(folder, filename+".py")

    local_file = os.path.exists(file_loc)

    statement = node.content
    aliases = []

    if " as " in statement:
        parts = statement.split()
        indexes = [i for i, part in enumerate(parts) if part == "as"]
        for index in indexes:
            actual_name = parts[index - 1]  # The name before "as"
            alias_name = parts[index + 1]    # The name after "as"

            alias = Alias(
                alias_name = alias_name,
                actual_name = actual_name,
                local_file = local_file
            )

            aliases.append(alias)

    return aliases

def alias_to_dict(alias: Alias) -> dict:
    return {
        'actual_name': alias.actual_name,
        'alias_name': alias.alias_name,
        'local_file': alias.local_file
    }

def node_to_dict(node):
    return {
        'type': node.type,
        'content': node.content,
        'functions': node.functions,
        'children': [node_to_dict(child) for child in node.children],
        'aliases': [alias_to_dict(alias) for alias in node.aliases if alias],
    }

def dict_to_node(data: Dict[str, Any]) -> Node:
    # Create the Node object from the dictionary
    node = Node(
        type=data['type'],
        content=data['content'],
        function=data.get('function'),
        alias=Alias(**data['alias']) if data.get('alias') else None
    )
    
    # Recursively convert children
    for child_data in data.get('children', []):
        child_node = dict_to_node(child_data)
        node.children.append(child_node)
    
    return node




def parse_python_to_nodes(script_folder, script_name, output_folder="nodes"):
    script_path = os.path.join(script_folder, script_name)

    filename, _ = os.path.splitext(script_name)
    filename = filename.replace("/", ".")
    filename = filename.replace("\\", ".")

    with open(script_path, 'r') as file:
        lines = file.readlines()

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    node_file = os.path.join(output_folder, filename + ".json")
    # if os.path.exists(node_file):
    #     return False

    root = Node(type='root', content='')
    stack = [root]
    current_indent = 0
    in_docstring = False
    docstring_content = []
    aliases = []

    def extract_function_name(line):
        match = re.findall(r'\b([a-zA-Z0-9_\.]+)\s*\(', line)
        return match if match else []  # Return a list of function names

    for line in lines:
        stripped_line = line.strip()
        indent = len(line) - len(line.lstrip())

        # Handle docstrings
        if '"""' in stripped_line:
            if not in_docstring:
                in_docstring = True
                docstring_content = [stripped_line]
            else:
                docstring_content.append(stripped_line)
                full_docstring = '\n'.join(docstring_content)
                node = Node(type='docstring', content=full_docstring)
                if stack:  # Ensure stack is not empty
                    stack[-1].children.append(node)
                in_docstring = False
                docstring_content = []
            continue

        if in_docstring:
            docstring_content.append(line.rstrip())
            continue

        if stripped_line == '' or stripped_line.startswith('#'):
            continue

        # Adjust stack based on indentation
        while stack and indent < current_indent:
            stack.pop()
            current_indent -= 4

        # Reset stack if it becomes empty
        if not stack:
            stack.append(root)  # Reset to root
            current_indent = 0

        # Handle definitions
        if stripped_line.startswith('class '):
            if 'BaseModel' in stripped_line:
                node = Node(type='custom_type', content=stripped_line)  # Set type to custom_type
            else:
                node = Node(type='class', content=stripped_line)  # Set type to class
            stack[-1].children.append(node)
            stack.append(node)  # Push the class node onto the stack
            current_indent = indent + 4

        elif stripped_line.startswith('def '):
            function_names = extract_function_name(stripped_line)
            node = Node(type='function', content=stripped_line, functions=function_names)
            stack[-1].children.append(node)
            stack.append(node)
            current_indent = indent + 4

        elif stripped_line.startswith('if ') or stripped_line.startswith('elif ') or stripped_line.startswith('else:'):
            node = Node(type='condition', content=stripped_line)
            stack[-1].children.append(node)
            if stripped_line.endswith(':'):
                stack.append(node)
                current_indent = indent + 4

        elif stripped_line.startswith('for ') or stripped_line.startswith('while '):
            node = Node(type='loop', content=stripped_line)
            stack[-1].children.append(node)
            if stripped_line.endswith(':'):
                stack.append(node)
                current_indent = indent + 4
                
        elif stripped_line.startswith('import ') or stripped_line.startswith('from '):
            node = Node(type='import', content=stripped_line)
            stack[-1].children.append(node)

            # Extract aliases from the import statement
            tmp_aliases = get_alias(node, script_folder)
            if tmp_aliases:
                aliases.extend(tmp_aliases)

            # Handle the filename and local file check
            filename = node.content.split(" ")[1]
            filename = filename.replace(".", "/")

            file_loc = os.path.join(script_folder, filename + ".py")

            local_file = os.path.exists(file_loc)

            if local_file:
                # Call parse_python_to_nodes only if the file exists
                parse_python_to_nodes(script_folder, filename + ".py", output_folder)

        elif '(' in stripped_line:
            function_names = extract_function_name(stripped_line)
            node = Node(type='function_call', content=stripped_line, functions=function_names)
            if function_names == []:
                node = Node(type='statement', content=stripped_line)
                stack[-1].children.append(node)
                continue
            
            for alias in aliases:
                for function in function_names:
                    if alias.alias_name in function.split("."):
                        node.aliases.append(alias)

            stack[-1].children.append(node)
        else:
            node = Node(type='statement', content=stripped_line)
            stack[-1].children.append(node)

    data = node_to_dict(root)
    with open(node_file, 'w') as json_file:
        json.dump(data, json_file, indent=4)

    return True

def collect_functions_and_classes(output_folder):
    # Dictionary to hold the results
    functions_dict = {}

    # Get all JSON files in the output folder
    json_files = glob.glob(os.path.join(output_folder, "*.json"))
    
    for json_file in json_files:
        # Extract the filename without the extension
        filename = os.path.splitext(os.path.basename(json_file))[0]
        
        with open(json_file, 'r') as file:
            data = json.load(file)

        root_node = dict_to_node(data)

        # Initialize a list to hold function names for this file
        function_list = []

        # Recursive function to traverse the nodes
        def traverse_nodes(node):
            # Add functions
            if node.type == 'function':
                method_name_start = node.content.split()[1]
                method_name = method_name_start.split("(")[0]
                function_list.append(method_name)  # Get the function name

            # Add class methods
            if node.type == 'class':
                class_name = node.content.split()[1].split(':')[0]  # Get the class name
                for child in node.children:
                    if child.type == 'function':
                        method_name_start = child.content.split()[1]  # Get the method name
                        method_name = method_name_start.split("(")[0]
                        function_list.append(f"{class_name}.{method_name}")

            # Traverse children
            for child in node.children:
                traverse_nodes(child)

        # Start traversing from the root node
        traverse_nodes(root_node)

        # Store the collected functions in the dictionary
        functions_dict[filename] = function_list

    return functions_dict


def main(script_path, script_name):
    parse_python_to_nodes(script_path, script_name, output_folder="nodes")
    x = collect_functions_and_classes(output_folder="nodes")
    for key in x.keys():
        print(key, x[key])

script_path = 'C:/Users/justl/Documents/folder'
script_name = "main.py"
root = main(script_path, script_name)