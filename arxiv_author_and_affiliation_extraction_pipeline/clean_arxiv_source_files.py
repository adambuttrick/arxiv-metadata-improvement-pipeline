import os
import sys
import json
import logging
import pathlib
import argparse
from datetime import datetime
from latex_cleaner import LaTeXCleaner

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='Process LaTeX source files.')
    parser.add_argument('-d', '--source_dir', type=pathlib.Path,
                        help='Directory containing LaTeX files')
    parser.add_argument('-o', '--output-format',
                        choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('-n', '--no-expand-macros',
                        action='store_true', help='Disable macro expansion')
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    return args


def find_tex_files(directory):
    tex_files = {}
    base_path = os.path.abspath(directory)
    for root, _, files in os.walk(directory):
        tex_files_in_dir = [f for f in files if f.endswith('.tex')]
        if tex_files_in_dir:
            rel_path = os.path.relpath(root, base_path)
            parent_dir = rel_path.split(os.sep)[0]
            if parent_dir not in tex_files:
                tex_files[parent_dir] = []
            tex_files[parent_dir].extend(
                [os.path.join(root, f) for f in tex_files_in_dir])

    return tex_files


def format_output(content, identifier, format='text'):
    if format == 'json':
        output = {
            'identifier': identifier,
            'text': content,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'latex'
        }
        return json.dumps(output, indent=2)
    return content


def create_output_dir(source_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = pathlib.Path(f"{timestamp}_{source_dir.name}_cleaned")
    output_dir.mkdir(exist_ok=True)
    return output_dir


def write_output(content, output_dir, identifier, format='text'):
    extension = 'json' if format == 'json' else 'txt'
    output_file = output_dir / f"{identifier}.{extension}"
    output_file.write_text(content, encoding='utf-8')
    logger.info(f"Output written to: {output_file}")


def main():
    args = parse_args()
    output_dir = create_output_dir(args.source_dir)
    logger.info(f"Created output directory: {output_dir}")
    try:
        tex_files_by_dir = find_tex_files(args.source_dir)
        cleaner = LaTeXCleaner(expand_macros=not args.no_expand_macros)
        for parent_dir, files in tex_files_by_dir.items():
            try:
                logger.info(f"Processing directory: {parent_dir}")
                all_content = []
                for tex_file in files:
                    cleaned_text = cleaner.clean_files([tex_file])
                    if cleaned_text:
                        all_content.append(cleaned_text)
                if all_content:
                    combined_content = "\n\n".join(all_content)
                    output = format_output(
                        combined_content, parent_dir, args.output_format)
                    write_output(output, output_dir,
                                 parent_dir, args.output_format)
                else:
                    logger.error(f"No valid content found in {parent_dir}")
            except Exception as e:
                logger.error(f"Error processing {parent_dir}: {e}")

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
