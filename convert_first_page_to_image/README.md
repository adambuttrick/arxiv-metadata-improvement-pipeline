# Convert first page of PDFs to images

Extracts the first page from multiple PDFs and converts them to images. It can process a single PDF, a directory of PDFs, or retrieve a PDF from arXiv using a DOI.

## Installation

1. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

2. Install Poppler:
   - This script requires Poppler for PDF processing. Install it from: https://poppler.freedesktop.org/
   - Make sure Poppler is in your system PATH after installation.

## Usage

```
python multi_pdf_extractor.py -i <input> [-o <output_directory>] [-d <arxiv_doi>]
```

- `-i`, `--input`: Path to a PDF file or directory containing PDFs (required)
- `-o`, `--output`: Path to the output directory for images (optional)
- `-d`, `--doi`: arXiv DOI of the paper

If no output directory is specified, a default directory with a timestamp will be created.


## Output

The script saves the extracted first pages as PNG images in the specified (or default) output directory. Each image is named after its source PDF file.