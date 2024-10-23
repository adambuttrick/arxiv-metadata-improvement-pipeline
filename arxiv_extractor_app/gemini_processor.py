import os
import json
import codecs
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from PIL import Image
from google.generativeai import configure, GenerativeModel, upload_file


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_processor.log'),
        logging.StreamHandler()
    ]
)


@dataclass
class ProcessingStatus:
    success: bool
    message: str
    timestamp: str
    response: dict = None
    error_details: str = None
    model_used: str = None
    upload_uri: str = None
    raw_response: str = None


class GeminiProcessor:
    MODEL_NAMES = {
        "flash": "gemini-1.5-flash",
        "pro": "gemini-1.5-pro",
        "8b": "gemini-1.5-flash-8b"
    }

    def __init__(self, api_key=None, model_choice="8b"):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing GeminiProcessor")
        self.last_status = None
        self.model_choice = model_choice
        self._setup_api(api_key)
        self._setup_schema()
        self.uploaded_file = None
        self.logger.info(f"GeminiProcessor initialized with model choice: {model_choice}")

    def _update_status(self, success, message, response=None, error_details=None,
                       model_used=None, upload_uri=None, raw_response=None):
        self.last_status = ProcessingStatus(
            success=success,
            message=message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            response=response,
            error_details=error_details,
            model_used=model_used,
            upload_uri=upload_uri,
            raw_response=raw_response
        )
        log_level = logging.INFO if success else logging.ERROR
        self.logger.log(log_level, f"Status updated: {message}")
        if error_details:
            self.logger.error(f"Error details: {error_details}")

    def clean_response(self, result):
        if not isinstance(result, dict) or "authors" not in result:
            return result

        for author in result["authors"]:
            if "affiliations" in author and isinstance(author["affiliations"], list):
                author["affiliations"] = [
                    aff.strip('"') for aff in author["affiliations"]
                ]
        return result

    def _setup_api(self, api_key):
        self.logger.info("Setting up API configuration")
        try:
            if api_key is None:
                api_key = os.environ.get("GEMINI_API_KEY")
                self.logger.debug("Using API key from environment variable")

            if not api_key:
                self.logger.error("No API key provided")
                raise ValueError(
                    "Gemini API key must be provided either as argument or "
                    "through GEMINI_API_KEY environment variable"
                )

            configure(api_key=api_key)
            self.model_name = self._get_model_name(self.model_choice)
            self.model = GenerativeModel(self.model_name)
            self.logger.info(f"API configured successfully with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to setup API: {str(e)}", exc_info=True)
            raise

    def _get_model_name(self, model_choice):
        model_name = self.MODEL_NAMES.get(model_choice, "gemini-1.5-flash-8b")
        self.logger.debug(f"Model name resolved: {model_name} for choice: {model_choice}")
        return model_name

    def _setup_schema(self):
        self.logger.debug("Setting up response schema")
        self.schema = {
            "type": "object",
            "properties": {
                "authors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string"},
                            "affiliations": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["author", "affiliations"]
                    }
                }
            },
            "required": ["authors"]
        }
        self.logger.debug("Schema setup complete")

    def process_image(self, image_path):
        self.logger.info(f"Starting image processing for: {image_path}")
        try:
            self._update_status(True, f"Uploading file: {image_path}")
            self.uploaded_file = upload_file(str(image_path))
            self.logger.info(f"File uploaded successfully: {self.uploaded_file.uri}")

            self._update_status(True, f"File uploaded successfully: {self.uploaded_file.uri}",
                                upload_uri=self.uploaded_file.uri)

            prompt = (
                "Analyze this image and identify the authors and their affiliations. "
                "Note that each author may have multiple affiliations. "
                "Return the information in a structured format where affiliations is an array. "
                "Do not include quotes around affiliation strings."
            )

            response = self.model.generate_content(
                [prompt, self.uploaded_file],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_schema": self.schema
                }
            )
            self.logger.debug(f"Raw response text: {response.text}")

            try:
                result = json.loads(response.text)
                result = self.clean_response(result)

                if self.validate_response(result):
                    arxiv_id = os.path.splitext(
                        os.path.basename(image_path))[0]
                    result["id"] = arxiv_id
                    result["doi"] = f"10.48550/arXiv.{arxiv_id}"

                    self._update_status(
                        True,
                        "Successfully extracted author information",
                        response=result,
                        model_used=self.model_name,
                        raw_response=response.text
                    )
                    return result

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {str(e)}")
                self.logger.error(f"Failed JSON content: {response.text}")
                self._update_status(
                    False,
                    "Failed to parse API response",
                    error_details=str(e),
                    model_used=self.model_name,
                    raw_response=response.text
                )
                return None

        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._update_status(
                False,
                error_msg,
                error_details=str(e),
                model_used=self.model_name
            )
            return None

        finally:
            if self.uploaded_file:
                try:
                    self.uploaded_file.delete()
                    self.logger.info(f"Deleted uploaded file: {self.uploaded_file.uri}")
                except Exception as e:
                    self.logger.error(f"Error deleting uploaded file: {str(e)}", exc_info=True)

    def save_json_output(self, result, output_path):
        self.logger.info(f"Attempting to save JSON output to: {output_path}")
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Successfully saved JSON output to: {output_path}")
            self._update_status(
                True,
                f"Saved JSON output to {output_path}",
                model_used=self.model_name
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON output: {str(e)}", exc_info=True)
            self._update_status(
                False,
                f"Error saving JSON output: {str(e)}",
                error_details=str(e),
                model_used=self.model_name
            )
            return False

    def validate_response(self, response):
        self.logger.debug("Starting response validation")
        try:
            if not isinstance(response, dict):
                self.logger.error(
                    "Validation failed: response is not a dictionary")
                return False
            if "authors" not in response:
                self.logger.error("Validation failed: 'authors' key missing")
                return False
            if not isinstance(response["authors"], list):
                self.logger.error("Validation failed: 'authors' is not a list")
                return False

            for idx, author in enumerate(response["authors"]):
                if not isinstance(author, dict):
                    self.logger.error(f"Validation failed: author {idx} is not a dictionary")
                    return False
                if "author" not in author or "affiliations" not in author:
                    self.logger.error(f"Validation failed: author {idx} missing required fields")
                    return False
                if not isinstance(author["author"], str):
                    self.logger.error(f"Validation failed: author {idx} name is not a string")
                    return False
                if not isinstance(author["affiliations"], list):
                    self.logger.error(f"Validation failed: author {idx} affiliations is not a list")
                    return False
                if not author["affiliations"]:
                    self.logger.error(f"Validation failed: author {idx} has empty affiliations")
                    return False
                if not all(isinstance(affiliation, str) for affiliation in author["affiliations"]):
                    self.logger.error(f"Validation failed: author {idx} has non-string affiliations")
                    return False

            self.logger.info("Response validation successful")
            return True
        except Exception as e:
            self.logger.error(f"Validation failed with exception: {str(e)}", exc_info=True)
            return False

    def get_processing_status(self):
        self.logger.debug("Retrieving processing status")
        return self.last_status

    def set_model(self, model_choice):
        self.logger.info(f"Attempting to set model to: {model_choice}")
        if model_choice not in self.MODEL_NAMES:
            error_msg = f"Invalid model choice. Must be one of: {', '.join(self.MODEL_NAMES.keys())}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.model_choice = model_choice
        self.model_name = self._get_model_name(model_choice)
        self.model = GenerativeModel(self.model_name)
        self.logger.info(f"Successfully set model to: {self.model_name}")
