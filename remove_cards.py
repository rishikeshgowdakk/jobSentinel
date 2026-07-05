import sys

def main():
    with open('frontend/src/App.jsx', 'r') as f:
        lines = f.readlines()

    new_lines = []
    
    # Ranges to delete (1-indexed to match text editors, inclusive)
    delete_ranges = [
        (510, 557), # Card A
        (559, 625), # Card B
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
            
        # Adjust grid to 1 col
        if line_num == 508 and 'md:grid-cols-3' in line:
            line = line.replace('md:grid-cols-3', 'md:grid-cols-1')
            
        new_lines.append(line)

    with open('frontend/src/App.jsx', 'w') as f:
        f.writelines(new_lines)
        
    print("Cards A and B removed successfully.")

if __name__ == '__main__':
    main()
