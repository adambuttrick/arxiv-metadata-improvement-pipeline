import os
import re
import sys
import logging
import argparse
import requests
from pdf2image import convert_from_path, convert_from_bytes
from PIL import Image

from datetime import datetime


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract the first page of PDF(s) and convert to images.")
    parser.add_argument("-i", "--input", required=True,
                        help="Path to a PDF file or directory containing PDFs")
    parser.add_argument("-o", "--output",
                        help="Output directory for images (default: timestamped directory)")
    parser.add_argument("-d", "--doi",
                        help="arXiv DOI of the paper (for backward compatibility)")
    return parser.parse_args()


def process_input(input_path):
    if os.path.isfile(input_path):
        if input_path.lower().endswith('.pdf'):
            return [input_path]
        else:
            raise ValueError(f"Input file is not a PDF: {input_path}")
    elif os.path.isdir(input_path):
        pdf_files = [os.path.join(input_path, f) for f in os.listdir(input_path)
                     if f.lower().endswith('.pdf')]
        if not pdf_files:
            raise ValueError(f"No PDF files found in directory: {input_path}")
        return pdf_files
    else:
        raise ValueError(f"Input path does not exist: {input_path}")


def extract_first_page(pdf_path):
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        return images[0]
    except Exception as e:
        logging.error(f"Error extracting first page from {pdf_path}: {e}")
        return None


def save_image(image, output_dir, filename):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{filename}.png")
    try:
        image.save(output_path)
        logging.info(f"Image saved successfully to {output_path}")
    except Exception as e:
        logging.error(f"Error saving image {filename}: {e}")


def extract_arxiv_id(doi_or_url):
    arxiv_pattern = r'((?:[\d.]+\/\d+)|(?:\d+\.\d+))'
    match = re.search(arxiv_pattern, doi_or_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid arXiv identifier or URL")


def retrieve_pdf(arxiv_id):
    base_url = "https://arxiv.org/pdf/"
    pdf_url = f"{base_url}{arxiv_id}.pdf"

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logging.error(f"Error retrieving PDF: {e}")
        return None


def process_arxiv(doi, output_dir):
    try:
        arxiv_id = extract_arxiv_id(doi)
        pdf_content = retrieve_pdf(arxiv_id)
        if pdf_content:
            images = convert_from_bytes(pdf_content, first_page=1, last_page=1)
            if images:
                save_image(images[0], output_dir, f"arxiv_{arxiv_id}")
            else:
                logging.error(f"Failed to convert arXiv PDF to image: {arxiv_id}")
        else:
            logging.error(f"Failed to retrieve arXiv PDF: {arxiv_id}")
    except ValueError as e:
        logging.error(f"Error processing arXiv DOI: {e}")


def main():
    args = parse_arguments()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    if args.output:
        output_dir = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"{timestamp}_1st_page_images"

    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory: {output_dir}")

    if args.doi:
        process_arxiv(args.doi, output_dir)
    else:
        try:
            pdf_paths = process_input(args.input)
            for pdf_path in pdf_paths:
                image = extract_first_page(pdf_path)
                if image:
                    filename = os.path.splitext(os.path.basename(pdf_path))[0]
                    save_image(image, output_dir, filename)
                else:
                    logging.warning(f"Skipping {pdf_path} due to extraction error")
        except ValueError as e:
            logging.error(f"Error processing input: {e}")
            sys.exit(1)
    logging.info("Processing completed.")


if __name__ == "__main__":
    main()
