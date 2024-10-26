# arXiv Author and Affiliation Extraction Pipeline

Data pipeline for extracting structured author and affiliation information from arXiv LaTeX source files.

## Overview

This pipeline processes arXiv LaTeX source files to extract and structure author affiliations, email addresses, and institutional relationships. It consists of three main components:

1. `clean_arxiv_source_files.py`: Does the initial processing of LaTeX source files
2. `latex_cleaner.py`: Cleans and normalizes tje LaTeX
3. `find_authors_affiliations_cleaned_source_files.py`: Extracts structured author/affiliation data from the normalized LaTeX

## Credit

The LaTeX cleaning functionality is largely derived from Together's RedPajama dataset preparation pipeline, specifically their [arXiv cleaner](https://github.com/togethercomputer/RedPajama-Data/blob/cc_metadata/data_prep/arxiv/arxiv_cleaner.py). The cleaning process has been modified to be more inclusive of all document parts and sections, as author and affiliation blocks appear to have been often excluded in the original implementation.

## Usage

```bash
# 1. Clean the LaTeX source files
python clean_arxiv_source_files.py -d /path/to/arxiv/sources -o text

# 2. Extract author and affiliation information
python find_authors_affiliations_cleaned_source_files.py -i /path/to/cleaned/files -o authors_affiliations.json --pretty
```

## Data Flow

The data is processed in three stages:

For the first stage, we traverses the directory structure to locate all of the .tex files. We maintains the hierarchical structure of the source by grouping files according to their parent directories, which typically represent individual papers or submissions.

These files then get passed to a LaTeX cleaning stage, where we prepare the text for structured extraction. The cleaner script removes LaTeX comments and normalizes whitespace while maintaining the document sections, recursively processesing any \input commands to consolidate split documents.

For the final extraction stage, we doe some detailed pattern matching to build the author-institution graph, first identifying all the author blocks through matching to various LaTeX commands like \author and \authors, etc. We then locate institutional affiliations marked by \institute, \affiliation, or \address tags. Connections between authors and institutions are made by tracking \inst{N} reference numbers and similar tags, whereas email addresses are associated with authors based on their relative document position. Throughout the pipeline, we also preserve surrounding context to allow for manual verification of the extractions and to provide further context by for subsequent LLM processing.

## Output Format

The pipeline generates a JSON file containing:
- Author blocks with any associated institution numbers
- Institution blocks with the full affiliation text
- Email addresses that were able to be linked to authors
- Surrounding context for blocks
- Processing metadata and error reporting

## Limitations

- Assumes plausible variations of LaTeX formatting for author, affiliation, email blocks, and thus may not capture all possible forms