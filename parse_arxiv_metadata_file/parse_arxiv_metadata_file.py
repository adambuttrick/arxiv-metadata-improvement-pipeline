import json
import csv
import os
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Parse arXiv JSON and categorize into CSV and JSON files.")
    parser.add_argument("-i", "--input_file",
                        help="Path to the input JSON file")
    parser.add_argument("-o", "--output_dir", default="arxiv_metadata",
                        help="Path to the output directory")
    return parser.parse_args()


def parse_json_file(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            yield json.loads(line.strip())


def process_categories(paper, base_output_dir):
    categories = paper.get('categories', 'uncategorized').split()
    category_paths = []
    for category in categories:
        category_path = os.path.join(base_output_dir, category)
        os.makedirs(category_path, exist_ok=True)
        category_paths.append((category, category_path))
    return category_paths


def append_to_csv(paper, category, category_path):
    csv_path = os.path.join(category_path, f'{category}.csv')
    file_exists = os.path.exists(csv_path)
    fieldnames = list(paper.keys()) + ['DOI']
    with open(csv_path, 'a', encoding='utf-8') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, escapechar='\\')
        if not file_exists:
            writer.writeheader()
        paper_copy = paper.copy()
        paper_copy['DOI'] = f"https://doi.org/10.48550/arXiv.{paper['id']}"
        for key, value in paper_copy.items():
            if isinstance(value, str):
                paper_copy[key] = value.replace('\n', ' ').replace('\r', '')
            elif value is None:
                paper_copy[key] = ''
            else:
                paper_copy[key] = str(value).replace('\n', ' ').replace('\r', '')
        writer.writerow(paper_copy)


def append_to_json(paper, category, category_path):
    json_path = os.path.join(category_path, f'{category}.json')
    paper_copy = paper.copy()
    paper_copy['DOI'] = f"https://doi.org/10.48550/arXiv.{paper['id']}"
    with open(json_path, 'a') as jsonfile:
        json.dump(paper_copy, jsonfile)
        jsonfile.write('\n')


def main():
    args = parse_arguments()
    try:
        for paper in parse_json_file(args.input_file):
            category_paths = process_categories(paper, args.output_dir)
            for category, category_path in category_paths:
                append_to_csv(paper, category, category_path)
                append_to_json(paper, category, category_path)
        print("Processing completed successfully.")
    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the input file.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()
