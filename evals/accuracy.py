import json
import argparse

def count_final_grade_A(filename):
    count = 0
    total_count = 0
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            total_count += 1          
            try:
                data = json.loads(line)
                if data.get("final_grade") == "A":
                    count += 1
            except json.JSONDecodeError:
                print("Skipping invalid JSON line.")
    return count, total_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate accurary from graded answers in a DataFrame')
    parser.add_argument('df_path', type=str, help='Path to the graded DataFrame JSON file')

    args = parser.parse_args()
    count, total_count = count_final_grade_A(args.df_path) 
    print(f"count={count}, total_count={total_count}, accuracy={count/total_count}")
