import re
import os

file_path = r'c:\Users\Usuario\Desktop\control_maestros\gestion_escolar\templates\gestion_escolar\base.html'
if not os.path.exists(file_path):
    print(f'Error: {file_path} not found')
    exit(1)

with open(file_path, 'rb') as f:
    raw_content = f.read()

if raw_content.startswith(b'\xef\xbb\xbf'):
    raw_content = raw_content[3:]

content = raw_content.decode('utf-8', errors='replace')

# Fix mojibake
replacements = {
    'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã±': 'ñ',
    'Ã\x81': 'Á', 'Ã\x89': 'É', 'Ã\x8d': 'Í', 'Ã\x93': 'Ó', 'Ã\x9a': 'Ú', 'Ã\x91': 'Ñ'
}
for k, v in replacements.items():
    content = content.replace(k, v)

# Fix broken template tags (multi-line to single-line) - MORE AGGRESSIVE
content = re.sub(r'\{\s*\{\s*', r'{{', content)
content = re.sub(r'\s*\}\s*\}', r'}}', content)
content = re.sub(r'\{\s*%\s*', r'{%', content)
content = re.sub(r'\s*%\s*\}', r'%}', content)

# Specific fix for style blocks: collapse all whitespace and then reformat carefully
def robust_style_fix(match):
    style_content = match.group(1)
    # Collapse all whitespace into single spaces
    style_content = re.sub(r'\s+', ' ', style_content)
    # Restore some basic spacing for properties
    style_content = style_content.replace('; ', ';\n            ').replace('{ ', ' {\n            ').replace('} ', '}\n        ')
    # Special case: linear-gradient should be compact but space after commas
    style_content = re.sub(r'linear-gradient\([^)]+\)', lambda m: m.group(0).replace(' ', ''), style_content)
    style_content = style_content.replace(',', ', ')
    return f'<style>{style_content}</style>'

content = re.sub(r'<style>(.*?)</style>', robust_style_fix, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print('Successfully applied FINAL ultra-robust fix')
