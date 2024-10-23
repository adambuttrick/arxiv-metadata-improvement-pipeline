# arXiv Author Extractor

Demo Streamlit app that extracts author and affiliation information from arXiv papers using Google's Gemini vision models and matches institutions to ROR IDs.

## Features

- Extract author and affiliation information from arXiv papers
- Support for both arXiv IDs/DOIs and direct PDF uploads
- Automatic matching of institutions to ROR IDs
- Gemini model options (8b, flash, pro)
- Configurable ROR/[Marple](https://gitlab.com/crossref/labs/marple) affiliation matching strategies
- JSON export functionality

## Prerequisites
- [Google Gemini API key](https://ai.google.dev/gemini-api/docs/api-key)
- Poppler (required for PDF processing)

### Installing Poppler

- **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`
- **Windows**: Download and install from [poppler releases](http://blog.alivate.com.au/poppler-windows/)

## Installation

1. Clone the repo:
```bash
git clone https://github.com/yourusername/arxiv-author-extractor.git
cd arxiv-author-extractor
```

2. Install the packages:
```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key as an environment variable:
```bash
export GEMINI_API_KEY='your-api-key-here'
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your web browser and navigate to the displayed URL (typically defaults to `http://localhost:8501`)

3. Choose your preferred input method:
   - Enter an arXiv ID or DOI
   - Upload a PDF directly

4. Configure processing options:
   - Select Gemini model (8b, flash, or pro)
   - Choose ROR matching strategy (single or multi)

5. Click "Process Paper" to start extraction


## Notes

- Only the first page of PDFs is processed to extract author information
- Processing time and performance varies depending on the selected Gemini model. 
- All models make mistakes so verify any and all results!