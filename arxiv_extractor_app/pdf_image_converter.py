import io
import os
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from PIL import Image
from pdf2image import convert_from_bytes, convert_from_path


@dataclass
class ConversionStatus:
    success: bool
    message: str
    timestamp: str
    image_size: tuple = None
    error_details: str = None


class PDFImageConverter:
    def __init__(self):
        self.last_status = None
        self.dpi = 200
        self._temp_dir = None

    def __enter__(self):
        self._temp_dir = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                for file in os.listdir(self._temp_dir):
                    os.remove(os.path.join(self._temp_dir, file))
                os.rmdir(self._temp_dir)
            except Exception as e:
                print(f"Warning: Error cleaning up temporary files: {e}")

    def convert_to_image(self, pdf_content):
        try:
            if isinstance(pdf_content, (str, Path)):
                images = convert_from_path(
                    pdf_content,
                    first_page=1,
                    last_page=1,
                    dpi=self.dpi
                )
            else:
                images = convert_from_bytes(
                    pdf_content,
                    first_page=1,
                    last_page=1,
                    dpi=self.dpi
                )

            if not images:
                self._update_status(False, "No pages converted from PDF")
                return None

            image = images[0]
            self._update_status(
                True,
                "Successfully converted first page to image",
                image_size=image.size
            )
            return image

        except Exception as e:
            self._update_status(False, f"Error converting PDF to image: {str(e)}", error_details=str(e))
            return None

    def save_image(self, image, output_path):
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)

            self._update_status(
                True,
                f"Image saved successfully to {output_path}",
                image_size=image.size
            )
            return True

        except Exception as e:
            self._update_status(False, f"Error saving image: {str(e)}", error_details=str(e))
            return False

    def get_image_bytes(self, image, format='PNG'):
        try:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format=format)
            img_byte_arr.seek(0)
            return img_byte_arr.getvalue()
        except Exception as e:
            self._update_status(False, f"Error converting image to bytes: {str(e)}", error_details=str(e))
            return None

    def _update_status(self, success, message, image_size=None, error_details=None):
        self.last_status = ConversionStatus(
            success=success,
            message=message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            image_size=image_size,
            error_details=error_details
        )

    def get_conversion_status(self):
        return self.last_status

    def set_dpi(self, dpi):
        self.dpi = dpi
