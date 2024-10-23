import re
import os
import requests
from datetime import datetime
from dataclasses import dataclass, field
from urllib.parse import urlparse, unquote


@dataclass
class DownloadStatus:
    success: bool
    message: str
    timestamp: str
    arxiv_id: str = None
    file_size: int = None


class ArxivPDFRetriever:
    def __init__(self):
        self.last_status = None
        self.base_url = "https://arxiv.org/pdf/"

    def validate_doi(self, doi):
        doi = doi.strip()
        if doi.startswith(('http://', 'https://')):
            doi = unquote(urlparse(doi).path.split('/')[-1])
        if doi.startswith('10.48550/arXiv.'):
            doi = doi.replace('10.48550/arXiv.', '')
        elif doi.startswith('10.48550/'):
            doi = doi.replace('10.48550/', '')

        arxiv_pattern = r'((?:\d{4}\.\d{4,5}(?:v\d+)?)|(?:\d{7})|(?:[a-z-]+(?:\.[A-Z]{2})?\/\d{7}(?:v\d+)?))'

        match = re.search(arxiv_pattern, doi)
        if match:
            return True, match.group(1)
        return False, "Invalid arXiv identifier format"

    def download_pdf(self, identifier):
        valid, arxiv_id = self.validate_doi(identifier)
        if not valid:
            self._update_status(False, arxiv_id, "Invalid identifier provided")
            return False, b''

        url = f"{self.base_url}{arxiv_id}.pdf"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            if not response.headers.get('content-type', '').startswith('application/pdf'):
                self._update_status(
                    False, arxiv_id, "Retrieved content is not a PDF")
                return False, b''

            content = response.content
            self._update_status(
                True,
                arxiv_id,
                "PDF downloaded successfully",
                len(content)
            )
            return True, content

        except requests.RequestException as e:
            error_msg = f"Error downloading PDF: {str(e)}"
            self._update_status(False, arxiv_id, error_msg)
            return False, b''

    def _update_status(self, success, arxiv_id, message, file_size=None):
        self.last_status = DownloadStatus(
            success=success,
            arxiv_id=arxiv_id,
            message=message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            file_size=file_size
        )

    def get_download_status(self):
        return self.last_status

    def extract_arxiv_id(self, identifier):
        valid, arxiv_id = self.validate_doi(identifier)
        if not valid:
            raise ValueError(arxiv_id)
        return arxiv_id
