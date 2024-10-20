# Gemini author and affiliation extraction

Processes images using the Google Gemini API to extract author and affiliation information. It can handle a single image or a directory of images, and outputs the results as JSON files.

## Installation

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up your Gemini API key:
   - Obtain a Gemini API key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)
   - Set the API key as an environment variable:
     ```
     export GEMINI_API_KEY=your_api_key_here
     ```

## Usage

```
python gemini_image_analysis.py -i <input> [-o <output_directory>] [-m <model>]
```

- `-i`, `--input`: Path to an image file or directory containing images (required)
- `-o`, `--output`: Path to the output directory for JSON files (optional)
- `-m`, `--model`: Model to use: "flash" (Gemini 1.5 Flash), "pro" (Gemini 1.5 Pro), or "8b" (Gemini 1.5 Flash 8B, default)

If no output directory is specified, a default directory with a timestamp will be created.

## Output

The script saves the extracted author and affiliation information as JSON files in the specified (or default) output directory. Each JSON file is named after its source image file and contains:

- An array of authors with their affiliations
- The arXiv ID (derived from the image filename)
- The corresponding DOI (10.48550/arXiv.{arXiv ID})

## Supported Image Formats

The Gemini Vision API supports the following image formats:
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- WebP (.webp)
- HEIC (.heic)
- HEIF (.heif)

## Error Handling

- If an image cannot be processed, an error message will be logged, but the script will continue processing images.
- If the API returns an invalid JSON response, the raw response will be saved instead.

## Notes

- The script uses the Gemini API, which requires uploading images for processing. Each image is uploaded, processed, and then deleted from the API's storage.