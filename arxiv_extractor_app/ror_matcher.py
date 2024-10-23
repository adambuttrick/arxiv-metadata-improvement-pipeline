import requests
import logging
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import quote


@dataclass
class MatchingStatus:
    success: bool
    message: str
    timestamp: str
    matches: dict = None
    error_details: str = None
    strategy_used: str = None


class RORMatcher:
    STRATEGIES = {
        "single": "affiliation-single-search",
        "multi": "affiliation-multi-search"
    }

    def __init__(self, strategy="single", verbose=False):
        self.last_status = None
        self.strategy = self.STRATEGIES.get(
            strategy, self.STRATEGIES["single"])
        self.verbose = verbose
        self.base_url = "https://marple.research.crossref.org/match"
        self._setup_logging()

    def _setup_logging(self):
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s %(levelname)s %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )

    def _update_status(self, success, message, matches=None, error_details=None):
        self.last_status = MatchingStatus(
            success=success,
            message=message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            matches=matches,
            error_details=error_details,
            strategy_used=self.strategy
        )

    def query_marple(self, affiliation):
        try:
            params = {
                "task": "affiliation-matching",
                "input": quote(affiliation),
                "strategy": self.strategy
            }
            url = f"{self.base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

            if self.verbose:
                logging.debug(f"Querying Marple API for: {affiliation}")

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            api_response = response.json()

            if api_response["status"] != "ok":
                raise ValueError("API returned non-OK status")

            matches = []
            for item in api_response["message"]["items"]:
                matches.append({
                    "id": item["id"],
                    "confidence": item["confidence"]
                })

            if self.verbose and matches:
                logging.debug(f"Found {len(matches)} matches for '{affiliation}'")
            elif self.verbose:
                logging.debug(f"No matches found for '{affiliation}'")

            return matches

        except requests.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if self.verbose:
                logging.error(error_msg)
            return None

        except Exception as e:
            error_msg = f"Error processing affiliation: {str(e)}"
            if self.verbose:
                logging.error(error_msg)
            return None

    def match_affiliations(self, data):
        if not isinstance(data, dict) or "authors" not in data:
            self._update_status(False, "Invalid input data format")
            return None

        try:
            enhanced_data = data.copy()
            all_matches = {}

            for author in enhanced_data["authors"]:
                if not isinstance(author.get("affiliations"), list):
                    continue
                full_affiliation = ", ".join(author["affiliations"])
                matches = self.query_marple(full_affiliation)

                author["affiliations"] = [{
                    "name": full_affiliation,
                    "ror_ids": matches if matches else []
                }]

                if matches:
                    all_matches[full_affiliation] = matches

            self._update_status(
                True,
                "Successfully processed affiliations",
                matches=all_matches if all_matches else None
            )
            return enhanced_data

        except Exception as e:
            self._update_status(
                False,
                "Error processing affiliations",
                error_details=str(e)
            )
            return None

    def set_strategy(self, strategy):
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Invalid strategy. Must be one of: {', '.join(self.STRATEGIES.keys())}")
        self.strategy = self.STRATEGIES[strategy]

    def get_matching_status(self):
        return self.last_status
