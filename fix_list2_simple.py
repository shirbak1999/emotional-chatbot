import re

# Read the file and process it line by line
with open('script.py', 'r') as f:
    lines = f.readlines()

# Process each line
for i, line in enumerate(lines):
    # Check if this line contains a key: value pattern
    if ':' in line and '"' in line and not line.strip().startswith('#'):
        # Extract the key part (everything before the colon)
        parts = line.split(':')
        if len(parts) >= 2:
            key_part = parts[0].strip()
            # If the key part ends with a quote, it's a proper string
            if key_part.endswith('"'):
                # Remove the value part and keep only the key
                new_line = key_part + ',\n'
                lines[i] = new_line

# Write the modified content back
with open('script.py', 'w') as f:
    f.writelines(lines)

print("Successfully processed script.py") 