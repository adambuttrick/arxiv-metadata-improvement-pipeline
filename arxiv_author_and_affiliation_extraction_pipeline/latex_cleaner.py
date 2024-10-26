import re
import os
import logging

logger = logging.getLogger(__name__)

class LaTeXCleaner:
    """Class for cleaning LaTeX documents."""
    
    def __init__(self, expand_macros=True):
        self.expand_macros = expand_macros
        
        # Patterns for identifying document sections
        self.section_pattern = re.compile(
            r"^(.*?)("
            r"\\\bchapter\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bpart\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bsection\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bsubsection\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bsubsubsection\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bparagraph\b\*?(?:\[(.*?)\])?\{(.*?)\}|"
            r"\\\bsubparagraph\b\*?(?:\[(.*?)\])?\{(.*?)\}"
            r")",
            re.DOTALL
        )
        
        self.end_pattern = re.compile(
            r"("
            r"\\appendix|"
            r"\\begin\{references\}|"
            r"\\begin\{REFERENCES\}|"
            r"\\begin\{thebibliography\}|"
            r"\\bibliography\{.*\}"
            r").*$",
            re.DOTALL
        )
        
        self.input_pattern = re.compile(r'\\input\{([^}]+)\}')

    def clean_files(self, file_paths):
        if not file_paths:
            logger.warning("No input files provided")
            return ""
        all_content = []
        macros = {}
        for path in file_paths:
            try:
                content = self._read_and_process_file(path, macros)
                if content:
                    all_content.append(content)
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")
                continue
        return "\n\n".join(all_content)

    def _read_and_process_file(self, path, macros, processed_files=None):
        if processed_files is None:
            processed_files = set()
        if path in processed_files:
            return ""  # Avoid circular inclusion
        processed_files.add(path)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, 'r', encoding='latin-1') as f:
                content = f.read()
        if self.expand_macros:
            macros.update(self._extract_macros(content))
        base_dir = os.path.dirname(path)
        def input_replacer(match):
            input_path = match.group(1)
            if not input_path.endswith('.tex'):
                input_path += '.tex'
            full_path = os.path.join(base_dir, input_path)
            if os.path.exists(full_path):
                return self._read_and_process_file(full_path, macros, processed_files)
            return ''    
        content = self.input_pattern.sub(input_replacer, content)
        
        return self._clean_content(content, macros)

    def _clean_content(self, content, macros):
        # Remove comments
        content = re.sub(r"(?m)^%.*\n?", "", content)  # Line comments
        content = re.sub(r"[^\\]%.+$", "", content, flags=re.MULTILINE)  # Inline comments
        
        # Remove content after appendix/bibliography
        content = self.end_pattern.sub("", content)
        
        # Expand macros if enabled
        if self.expand_macros and macros:
            content = self._expand_macros(content, macros)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content

    def _extract_macros(self, content):
        macros = {}

        # Extract \newcommand macros
        newcommand_pattern = r'\\\bnewcommand\b\*?\{(\\[a-zA-Z0-9]+?)\}\{(.*?)\}$'
        for match in re.finditer(newcommand_pattern, content, re.MULTILINE):
            macro_name = match.group(1).encode("unicode-escape").decode("utf-8")
            macro_value = match.group(2).encode("unicode-escape").decode("utf-8")
            macros[macro_name] = macro_value
            
        # Extract \def macros
        def_pattern = r'\\def\s*(\\[a-zA-Z0-9]+?)\s*\{(.*?)\}$'
        for match in re.finditer(def_pattern, content, re.MULTILINE):
            macro_name = match.group(1).encode("unicode-escape").decode("utf-8")
            macro_value = match.group(2).encode("unicode-escape").decode("utf-8")
            macros[macro_name] = macro_value
            
        return macros

    def _expand_macros(self, content, macros):
        modified_content = content
        for macro_name, macro_value in macros.items():
            modified_content = re.sub(
                r"(" + macro_name + r")" + r"([^a-zA-Z0-9])",
                macro_value + r"\2",
                modified_content
            )
        return modified_content