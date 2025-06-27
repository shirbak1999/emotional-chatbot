import re

# Read the file
with open('script.py', 'r') as f:
    content = f.read()

# Use regex to find and replace patterns like "key": value with just "key"
# This pattern matches: "something": followed by any value and optional comma
pattern = r'(".*?"):\s*[^,\n]*(?:,|\n)'
replacement = r'\1,\n'

# Apply the replacement
new_content = re.sub(pattern, replacement, content)

# Write the modified content back
with open('script.py', 'w') as f:
    f.write(new_content)

print("Successfully processed script.py with regex") 