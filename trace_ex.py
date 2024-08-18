import re

def get_used_functions(script_path):
    with open(script_path, 'r') as file:
        content = file.read()

    # Regular expression to find function calls
    # This looks for any characters (non-greedy) followed by an opening parenthesis,
    # capturing everything after the last whitespace or start of the line
    pattern = r'(^|[\s])([^\s]+?)\s*\('

    # Find all matches
    matches = re.findall(pattern, content, re.MULTILINE)

    # Extract the full function names (second group in each match)
    used_functions = set(match[1] for match in matches)

    return used_functions

# Example usage
# script_path = 'C:/Users/justl/Documents/VideoDiarization/main_v3.py'
# functions = get_used_functions(script_path)
# print("Functions potentially used in the script:")
# for func in sorted(functions):
#     print(f"  {func}")

# Example usage
script_path = 'C:/Users/justl/Documents/VideoDiarization/main_v3.py'
functions = get_used_functions(script_path)
print("Functions potentially used in the script:", functions)
