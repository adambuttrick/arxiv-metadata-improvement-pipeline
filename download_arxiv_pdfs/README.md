# arXiv PDF downloader

Downloads arXiv PDFs based on IDs provided in a CSV file input.


## Installation
```
pip install -r requirements.txt
```

## Usage

```
python download_arxiv_pdfs.py -i <input_csv> -o <output_directory> [-v]
```

- `-i`, `--input_csv`: Path to the input CSV file (required)
- `-o`, `--output_dir`: Path to the output directory for downloaded PDFs (optional)
- `-v`, `--verbose`: Increase output verbosity (optional)

If no output directory is specified, a default directory with a timestamp will be created.

## Input CSV Format

The input CSV should have a column named 'id' containing arXiv paper IDs.

## Output

The script downloads PDFs to the specified (or default) output directory, naming each file with its arXiv ID.
