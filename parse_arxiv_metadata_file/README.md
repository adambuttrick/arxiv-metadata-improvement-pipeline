# arXiv metadata parser

Parses arXiv metadata from a JSON file and categorizes it into CSV and JSON files by subject category.

## Prerequisites
- Download the arXiv metadata dataset (available on [Kaggle](https://www.kaggle.com/datasets/Cornell-University/arxiv))

## Usage

```
python parse_arxiv_metadata_file.py -i <input_file> -o <output_directory>
```

- `-i`, `--input_file`: Path to the input JSON file (required)
- `-o`, `--output_dir`: Path to the output directory (default: "arxiv_metadata")

## Output

The script generates:
- A directory for each arXiv category
- Within each category directory:
  - A CSV file containing all papers in that category
  - A JSON file containing all papers in that category

Each paper entry in the CSV output also includes a DOI link.
