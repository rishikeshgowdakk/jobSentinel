import re

with open('App.jsx', 'r') as f:
    content = f.read()

# Replace invalid tailwind classes
replacements = {
    'slate-250': 'slate-200',
    'slate-350': 'slate-300',
    'slate-450': 'slate-400',
    'slate-550': 'slate-500',
    'slate-505': 'slate-500',
    'slate-555': 'slate-500',
    'slate-650': 'slate-600',
    'slate-750': 'slate-700',
    'slate-850': 'slate-800',
    'slate-955': 'slate-950',
    'red-955': 'red-950',
    'red-650': 'red-600',
    'emerald-450': 'emerald-400',
    'emerald-650': 'emerald-600'
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('App.jsx', 'w') as f:
    f.write(content)

print("Colors fixed")
