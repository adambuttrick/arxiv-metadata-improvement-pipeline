import re
import json
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description='Extract author and affiliation text blocks from LaTeX files')
    parser.add_argument(
        '-i', '--input', help='Input directory containing LaTeX text files', required=True)
    parser.add_argument(
        '-o', '--output', default='extracted_blocks.json', help='Output JSON file')
    parser.add_argument('-p', '--pretty', action='store_true',
                        help='Pretty print JSON output')
    return parser.parse_args()


def match_nested_braces(text, start):
    stack = []
    pos = start
    if text[pos] != '{':
        return None, start
    content = text[start]
    pos += 1
    
    while pos < len(text):
        char = text[pos]
        content += char
        if char == '{':
            stack.append(char)
        elif char == '}':
            if not stack:
                return content, pos + 1
            stack.pop()
        pos += 1
    
    return None, start


def extract_latex_blocks(content):
    patterns = {
        'author_blocks': [
            (r'\\author', 5),
            (r'\\authors', 5),
            (r'\\authorrunning', 5),
        ],
        'affiliation_blocks': [
            (r'\\institute', 5),
            (r'\\affiliation', 5),
            (r'\\address', 5),
            (r'\\institution', 5),
            (r'\\affil', 5),
        ],
        'email_blocks': [
            (r'\\email', 3),
            (r'\\Email', 3),
        ]
    }
    
    results = {
        'author_blocks': [],
        'affiliation_blocks': [],
        'email_blocks': [],
        'surrounding_context': []
    }
    for block_type, pattern_list in patterns.items():
        for pattern, context_size in pattern_list:
            pos = 0
            while True:
                match = re.search(pattern, content[pos:], re.DOTALL | re.MULTILINE)
                if not match:
                    break
                start_pos = pos + match.start()
                command_pos = pos + match.end()
                next_char_pos = command_pos
                while next_char_pos < len(content) and content[next_char_pos].isspace():
                    next_char_pos += 1
                if next_char_pos >= len(content) or content[next_char_pos] != '{':
                    pos = command_pos + 1
                    continue
                full_command = content[start_pos:next_char_pos]
                nested_content, end_pos = match_nested_braces(content, next_char_pos)
                if nested_content is None:
                    pos = command_pos + 1
                    continue
                full_match = full_command + nested_content
                context_start = max(0, start_pos - context_size)
                context_end = min(len(content), end_pos + context_size)
                context = content[context_start:context_end]
                results[block_type].append(full_match)
                results['surrounding_context'].append({
                    'block': full_match,
                    'context': context,
                    'position': start_pos,
                    'block_end': end_pos
                })
                pos = end_pos
    return results


def extract_block_associations(content):
    blocks = extract_latex_blocks(content)
    # Sort all blocks by position to understand order
    all_blocks = []
    for block_type in ['author_blocks', 'affiliation_blocks', 'email_blocks']:
        for block in blocks[block_type]:
            ctx = next((c for c in blocks['surrounding_context'] if c['block'] == block), None)
            if ctx:
                all_blocks.append({
                    'type': block_type,
                    'content': block,
                    'position': ctx['position'],
                    'block_end': ctx['block_end']
                })
    all_blocks.sort(key=lambda x: x['position'])
    # Extract institution numbers and references
    inst_pattern = r'\\inst{(\d+)}'
    author_insts = {}
    inst_blocks = {}
    # First pass - collect institution references
    for block in all_blocks:
        if block['type'] == 'author_blocks':
            # Find all \inst{N} references in author block
            insts = re.finditer(inst_pattern, block['content'])
            authors = [a.strip() for a in re.split(r'\\and', block['content'])]
            current_inst = None
            for author in authors:
                # Find institution reference for this author
                inst_match = re.search(inst_pattern, author)
                if inst_match:
                    current_inst = inst_match.group(1)
                if current_inst:
                    author_clean = re.sub(inst_pattern, '', author).strip()
                    author_clean = re.sub(r'[{}]', '', author_clean)
                    author_insts[author_clean] = current_inst
    # Second pass - match institutions
    current_inst_num = 1
    for block in all_blocks:
        if block['type'] == 'affiliation_blocks':
            affiliations = [a.strip() for a in re.split(r'\\and', block['content'])]
            for affiliation in affiliations:
                inst_blocks[str(current_inst_num)] = affiliation
                current_inst_num += 1
    associations = {
        'author_institutions': author_insts,
        'institution_blocks': inst_blocks,
        'ordered_blocks': all_blocks,
        'email_associations': {}
    }
    
    for block in all_blocks:
        if block['type'] == 'email_blocks':
            email = re.search(r'{([^}]+)}', block['content'])
            if email:
                email_addr = email.group(1)
                prev_authors = [b for b in all_blocks 
                              if b['type'] == 'author_blocks' 
                              and b['position'] < block['position']]
                if prev_authors:
                    nearest_author = prev_authors[-1]
                    associations['email_associations'][email_addr] = nearest_author['content']
    
    return associations

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = extract_latex_blocks(content)
        associations = extract_block_associations(content)
        return {
            'file_id': file_path.stem,
            'blocks': blocks,
            'associations': associations,
            'success': True
        }
    except Exception as e:
        return {
            'file_id': file_path.stem,
            'error': str(e),
            'success': False
        }


def main():
    try:
        args = parse_args()
        input_dir = Path(args.input)
        output_path = Path(args.output)
        if not input_dir.is_dir():
            raise NotADirectoryError(f"Input must be a directory: {args.input}")
        results = []
        for file_path in input_dir.glob('*.txt'):
            result = process_file(file_path)
            results.append(result)
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        output = {
            'metadata': {
                'total_files': len(results),
                'successful_files': len(successful),
                'failed_files': len(failed),
                'failed_file_list': [{'file_id': r['file_id'], 'error': r['error']} for r in failed]
            },
            'extracted_blocks': successful
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2 if args.pretty else None,
                      ensure_ascii=False)
        print(f"\nProcessing complete:")
        print(f"Total files: {output['metadata']['total_files']}")
        print(f"Successfully processed: {output['metadata']['successful_files']}")
        print(f"Failed: {len(failed)}")
        if failed:
            print("\nFailed files:")
            for failure in output['metadata']['failed_file_list']:
                print(f"  {failure['file_id']}: {failure['error']}")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
