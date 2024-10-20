import os
import json
import codecs
import argparse
import datetime
from google.generativeai import configure, GenerativeModel, upload_file


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process images with Google Generative AI API")
    parser.add_argument(
        "-i", "--input", help="Path to an image file or directory of images", required=True)
    parser.add_argument(
        "-o", "--output", help="Output directory for JSON files", default=None)
    parser.add_argument("-m", "--model", choices=["flash", "pro", "8b"], default="8b",
                        help="Model to use: flash (Flash 1.5), pro (Pro 1.5), or 8b (default)")
    return parser.parse_args()


def process_images(input_path):
    if os.path.isfile(input_path):
        return [input_path]
    elif os.path.isdir(input_path):
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif',
                            '.bmp', '.webp', '.heic', '.heif')
        return [os.path.join(input_path, f) for f in os.listdir(input_path)
                if f.lower().endswith(image_extensions)]
    else:
        raise ValueError(f"Invalid input path: {input_path}")


def get_model_name(model_choice):
    model_names = {
        "flash": "gemini-1.5-flash",
        "pro": "gemini-1.5-pro",
        "8b": "gemini-1.5-flash-8b"
    }
    return model_names.get(model_choice, "gemini-1.5-flash-8B")


def query_genai_api(image_path, model_choice):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    configure(api_key=api_key)
    model_name = get_model_name(model_choice)
    model = GenerativeModel(model_name)
    # The Gemini API requires we first upload the file to process instead of
    # sending as a direct input, so we do this then delete from the file storage.
    try:
        print(f"Uploading file: {image_path}")
        uploaded_file = upload_file(image_path)
        print(f"File uploaded successfully: {uploaded_file.uri}")

        schema = {
            "type": "object",
            "properties": {
                "authors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string"},
                            "affiliation": {"type": "string"}
                        },
                        "required": ["author", "affiliation"]
                    }
                }
            },
            "required": ["authors"]
        }
        prompt = "Analyze this image and identify the authors and their affiliations."
        response = model.generate_content(
            [prompt, uploaded_file],
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        uploaded_file.delete()
        print(f"Deleted uploaded file: {uploaded_file.uri}")
        return response.text

    except Exception as e:
        print(f"Error in query_genai_api: {e}")
        # Ensures we delete the file even if an error occurs
        if 'uploaded_file' in locals():
            try:
                uploaded_file.delete()
                print(f"Deleted uploaded file after error: {uploaded_file.uri}")
            except Exception as delete_error:
                print(f"Error deleting file: {delete_error}")
        raise


def save_json_output(api_response, image_filename, output_dir):
    json_filename = os.path.splitext(
        os.path.basename(image_filename))[0] + ".json"
    json_path = os.path.join(output_dir, json_filename)
    try:
        decoded_response = codecs.decode(api_response, 'unicode_escape')
        json_data = json.loads(decoded_response)
        arxiv_id = os.path.splitext(os.path.basename(image_filename))[0]
        json_data["id"] = arxiv_id
        json_data["doi"] = f"10.48550/arXiv.{arxiv_id}"
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON response for {image_filename}. Saving raw response.")
        json_data = {"raw_response": api_response}
    
    with open(json_path, "w", encoding='utf-8') as json_file:
        json.dump(json_data, json_file, indent=2, ensure_ascii=False)
    print(f"Saved JSON output for {image_filename} to {json_path}")


def main():
    args = parse_arguments()
    try:
        image_paths = process_images(args.input)
    except ValueError as e:
        print(f"Error: {e}")
        return
    if args.output:
        output_dir = args.output
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"gemini_responses_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving all JSON outputs to: {output_dir}")
    for image_path in image_paths:
        try:
            api_response = query_genai_api(image_path, args.model)
            save_json_output(api_response, image_path, output_dir)
        except Exception as e:
            print(f"Error processing {image_path}: {e}")


if __name__ == "__main__":
    main()
