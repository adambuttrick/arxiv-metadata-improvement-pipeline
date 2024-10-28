# arXiv source file downloader

Downloads LaTeX source files from arXiv papers using paper IDs from a CSV file.

## Installation

```
pip install -r requirements.txt
```

## Usage

```bash
python arxiv_latex_dl.py -i input.csv [-o output_dir] [-c column_name] [-p page_size] [-d delay_seconds] [-n num_retries] [-v]
```

## Arguments

- `-i, --input-file`: CSV file containing arXiv IDs (required)
- `-o, --output-dir`: Custom output directory (default: timestamp_csvname_latex_files)
- `-c, --column-name`: Name of column containing arXiv IDs (default: 'id')
- `-p, --page-size`: API request page size (default: 100)
- `-d, --delay-seconds`: Delay between API requests (default: 0.0)
- `-n, --num-retries`: Number of download retries (default: 3)
- `-v, --verbose`: Enable verbose logging

## Output

Creates a directory containing subdirectories for each paper, with extracted LaTeX source files in a `source` subfolder.

## Example

```bash
python arxiv_latex_dl.py -i papers.csv -c arxiv_id
```