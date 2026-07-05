import sys

def main():
    with open('frontend/src/App.jsx', 'r') as f:
        lines = f.readlines()

    new_lines = []
    
    # Ranges to delete (1-indexed to match text editors, inclusive)
    delete_ranges = [
        (758, 765), # Match Success in job card
        (779, 842), # Market Splits
        (892, 923), # Logs Console
        (926, 955), # Pipeline Tracker
    ]
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Check if line falls in any delete range
        skip = False
        for start, end in delete_ranges:
            if start <= line_num <= end:
                skip = True
                break
        
        if skip:
            continue
            
        # Adjust column spans
        if line_num == 697 and 'lg:col-span-8' in line:
            line = line.replace('lg:col-span-8', 'lg:col-span-12')
            
        if line_num == 849 and 'lg:col-span-6' in line:
            line = line.replace('lg:col-span-6', 'lg:col-span-12')
            
        new_lines.append(line)

    with open('frontend/src/App.jsx', 'w') as f:
        f.writelines(new_lines)
        
    print("UI components removed and spans adjusted successfully.")

if __name__ == '__main__':
    main()
