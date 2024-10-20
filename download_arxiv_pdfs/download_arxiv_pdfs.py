import argparse
import csv
import os
import requests
from datetime import datetime


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Download arXiv PDFs based on IDs from a CSV file.")
    parser.add_argument("-i", "--input_csv", help="Path to the input CSV file")
    parser.add_argument("-o", "--output_dir",
                        help="Path to the output directory for downloaded PDFs")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Increase output verbosity")
    return parser.parse_args()


def get_default_output_dir():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_arxiv_pdfs"


def parse_csv(csv_file_path):
    arxiv_ids = []
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            arxiv_ids.append(row['id'])
    return arxiv_ids


def download_pdf(arxiv_id, output_dir):
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    output_path = os.path.join(output_dir, f"{arxiv_id}.pdf")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(output_path, 'wb') as file:
            file.write(response.content)
        return True
    except requests.RequestException as e:
        print(f"Error downloading {arxiv_id}: {str(e)}")
        return False
    except IOError as e:
        print(f"Error saving {arxiv_id}: {str(e)}")
        return False


def main():
    args = parse_arguments()
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = get_default_output_dir()
        print(f"No output directory specified. Using default: {output_dir}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    arxiv_ids = parse_csv(args.input_csv)
    total_ids = len(arxiv_ids)
    successful_downloads = 0
    for i, arxiv_id in enumerate(arxiv_ids, 1):
        if args.verbose:
            print(f"Downloading {i}/{total_ids}: {arxiv_id}")
        if download_pdf(arxiv_id, output_dir):
            successful_downloads += 1
    print(f"\nDownload complete. Successfully downloaded {successful_downloads}/{total_ids} PDFs.")
    print(f"PDFs saved in: {os.path.abspath(output_dir)}")


if __name__ == "__main__":
    main()
