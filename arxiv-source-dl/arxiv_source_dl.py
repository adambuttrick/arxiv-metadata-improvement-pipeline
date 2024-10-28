import re
import os
import sys
import json
import logging
import shutil
import tarfile
import argparse
import arxiv
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from pathlib import Path


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Download LaTeX source files from arXiv papers listed in a CSV file.')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Path to CSV file containing arXiv IDs')
    parser.add_argument('-o', '--output-dir',
                        help='Custom output directory name (optional)')
    parser.add_argument('-c', '--column-name', default='id',
                        help='Name of column containing arXiv IDs (default: arxiv_id)')
    parser.add_argument('-p', '--page-size', type=int, default=100,
                        help='arxiv.py client page size (default: 100)')
    parser.add_argument('-d', '--delay-seconds', type=float, default=0.0,
                        help='Delay between API requests in seconds (default: 3.0)')
    parser.add_argument('-n', '--num-retries', type=int, default=3,
                        help='Number of download retries (default: 3)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    return args


def read_csv_file(csv_path, column_name):
    try:
        df = pd.read_csv(csv_path)
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in CSV file")
        return df
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise


def extract_arxiv_ids(df, column_name):
    return df[column_name].dropna().unique().tolist()


def is_valid_arxiv_id(arxiv_id):
    new_style = re.compile(r'^\d{4}\.\d{4,5}(v\d+)?$')
    old_style = re.compile(r'^[a-z-]+/\d{7}(v\d+)?$')
    return bool(new_style.match(str(arxiv_id)) or old_style.match(str(arxiv_id)))


def validate_arxiv_ids(arxiv_ids):
    valid_ids = []
    invalid_ids = []
    for arxiv_id in arxiv_ids:
        if is_valid_arxiv_id(arxiv_id):
            valid_ids.append(str(arxiv_id))
        else:
            invalid_ids.append(str(arxiv_id))
    if invalid_ids:
        logger.warning(f"Found {len(invalid_ids)} invalid arXiv IDs: {invalid_ids}")
    return valid_ids


def create_output_directory(input_file, base_name, timestamp):
    if base_name:
        dir_name = base_name
    else:
        csv_name = Path(input_file).stem
        dir_name = f"{timestamp}_{csv_name}_latex_files"
    output_dir = Path(dir_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def create_paper_directory(output_dir, arxiv_id):
    paper_dir = output_dir / arxiv_id / 'source'
    paper_dir.mkdir(parents=True, exist_ok=True)
    return paper_dir.parent


def cleanup_on_failure(directory):
    try:
        shutil.rmtree(directory)
        logger.debug(f"Cleaned up directory after failure: {directory}")
    except Exception as e:
        logger.warning(f"Failed to clean up directory {directory}: {e}")


def initialize_arxiv_client(page_size, delay_seconds, num_retries):
    return arxiv.Client(page_size=page_size, delay_seconds=delay_seconds, num_retries=num_retries)


def extract_tar_gz(tar_path, extract_path):
    try:
        with tarfile.open(tar_path, 'r:gz') as tar:
            def is_within_limits(member):
                return member.size < 50_000_000
            members = [m for m in tar.getmembers() if is_within_limits(m)]
            tar.extractall(path=extract_path, members=members)
        return True
    except Exception as e:
        logger.error(f"Failed to extract {tar_path}: {e}")
        return False


def download_single_paper(client, arxiv_id, paper_dir):
    try:
        paper = next(client.results(arxiv.Search(id_list=[arxiv_id])))
        source_path = paper_dir / 'source.tar.gz'
        paper.download_source(dirpath=str(paper_dir), filename='source.tar.gz')
        return extract_tar_gz(source_path, paper_dir / 'source')
    except Exception as e:
        logger.error(f"Failed to download {arxiv_id}: {e}")
        if paper_dir.exists():
            cleanup_on_failure(paper_dir)
        return False


def process_papers(client, arxiv_ids, output_dir):
    results = []
    for arxiv_id in tqdm(arxiv_ids, desc="Downloading papers"):
        paper_dir = create_paper_directory(output_dir, arxiv_id)
        success = download_single_paper(client, arxiv_id, paper_dir)
        results.append(
            {'arxiv_id': arxiv_id, 'status': 'success' if success else 'failed'})
    return results


def main():
    try:
        args = parse_args()
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        df = read_csv_file(args.input_file, args.column_name)
        arxiv_ids = extract_arxiv_ids(df, args.column_name)
        valid_ids = validate_arxiv_ids(arxiv_ids)
        if not valid_ids:
            logger.error("No valid arXiv IDs found in CSV")
            sys.exit(1)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = create_output_directory(args.input_file, args.output_dir, timestamp)
        client = initialize_arxiv_client(
            args.page_size, args.delay_seconds, args.num_retries)
        logger.info(f"Starting download of {len(valid_ids)} papers")
        results = process_papers(client, valid_ids, output_dir)
        success_count = sum(1 for r in results if r['status'] == 'success')
        logger.info(f"Download complete. Successfully downloaded {success_count}/{len(valid_ids)} papers")
        logger.info(f"Results saved in: {output_dir}")
    except Exception as e:
        logger.error(f"Process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
