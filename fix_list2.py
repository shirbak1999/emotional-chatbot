import re

# Read the original file
with open('script.py', 'r') as f:
    content = f.read()

# Find the list2 section
list2_start = content.find('list2=["')
if list2_start == -1:
    print("Could not find list2 in the file")

    
    exit(1)

# Find the end of list2 (look for the closing bracket)
list2_end = content.find(']', list2_start)
if list2_end == -1:
    print("Could not find end of list2")
    exit(1)

# Extract the list2 content
list2_content = content[list2_start:list2_end + 1]

# Split into lines and process each line
lines = list2_content.split('\n')
processed_lines = []

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Remove the opening bracket from the first line
    if line.startswith('list2=["'):
        line = line[7:]  # Remove 'list2=["'
    elif line.startswith('list2=['):
        line = line[6:]  # Remove 'list2=['
    
    # Remove the closing bracket from the last line
    if line.endswith(']'):
        line = line[:-1]
    
    # Skip empty lines
    if not line:
        continue
    
    # Remove trailing comma if present
    if line.endswith(','):
        line = line[:-1]
    
    # Check if this line has a colon (key: value format)
    if ':' in line and not line.startswith('"') and not line.startswith("'"):
        # This is a key: value format, extract just the key
        key = line.split(':')[0].strip()
        # Remove quotes if present
        if key.startswith('"') and key.endswith('"'):
            key = key[1:-1]
        elif key.startswith("'") and key.endswith("'"):
            key = key[1:-1]
        # Add quotes back and comma
        processed_lines.append(f'            "{key}",')
    else:
        # This is already a proper string, just add it back
        if not line.startswith('"') and not line.startswith("'"):
            # Add quotes if missing
            line = f'"{line}"'
        processed_lines.append(f'            {line},')

# Reconstruct the list2
new_list2 = 'list2=[\n' + '\n'.join(processed_lines) + '\n]'

# Replace the old list2 with the new one
new_content = content[:list2_start] + new_list2 + content[list2_end + 1:]

# Write the fixed content back to the file
with open('script.py', 'w') as f:
    f.write(new_content)

print("Successfully fixed list2 in script.py") 