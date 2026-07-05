import sys

with open('frontend/src/App.jsx', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # Match success in job card (approx line 758-765)
    if '<div className="text-right">' in line and 'font-mono' in lines[i+1] and 'Match' in lines[i+5]:
        skip = True
    
    if skip and '</div>' in line and 'Match' in lines[i-1]:
        skip = False
        continue
    
    if skip and i >= 750 and i <= 770:
        continue

    # Market Splits (779-841)
    if '{/* Right Side: Market Splits (1/3 width) */}' in line:
        skip = True
    
    if skip and i > 778 and i < 842 and '</div>' in line and lines[i+2].strip() == '</div>':
        # wait, just use line numbers for exact blocks since we know them
        pass

