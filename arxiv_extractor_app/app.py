import io
import os
import json
import base64
import tempfile
from pathlib import Path
from datetime import datetime
import streamlit as st
from arxiv_pdf_retriever import ArxivPDFRetriever
from pdf_image_converter import PDFImageConverter
from gemini_processor import GeminiProcessor
from ror_matcher import RORMatcher
from image_handler import ImageHandler


st.set_page_config(
    page_title="arXiv Author and Affiliation Extractor",
    page_icon="📚",
    layout="wide"
)

if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = None

image_handler = ImageHandler()


def save_uploaded_file(uploaded_file):
    try:
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            return Path(tmp_file.name)
    except Exception as e:
        st.error(f"Error saving uploaded file: {e}")
        return None


def load_api_key():
    if st.session_state.api_key:
        return st.session_state.api_key
    return os.environ.get("GEMINI_API_KEY")


def display_json(data):
    st.json(data)


def display_enhanced_results(data):
    st.subheader("Author Information")
    if "doi" in data and "arXiv" in data["doi"]:
        arxiv_id = data["doi"].replace("10.48550/arXiv.", "")
        st.markdown(f"📄 [View PDF on arXiv](https://arxiv.org/pdf/{arxiv_id}.pdf)")
    for author in data["authors"]:
        with st.expander(f"👤 {author['author']}", expanded=True):
            for aff in author["affiliations"]:
                st.write("🏛️ " + aff["name"])
                if aff["ror_ids"]:
                    for ror in aff["ror_ids"]:
                        confidence = f"{ror['confidence']*100:.1f}%" if isinstance(
                            ror['confidence'], float) else f"{ror['confidence']}%"
                        st.write(
                            f"   🔍 ROR ID: [{ror['id']}](https://ror.org/{ror['id'].split('/')[-1]}) (Confidence: {confidence})")
                else:
                    st.write("   ❌ No ROR ID match found")
    json_str = json.dumps(data, indent=2)
    st.download_button(
        label="Download JSON",
        data=json_str,
        file_name="author_info.json",
        mime="application/json"
    )


def add_to_history(step, status, details):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.processing_history.append({
        "timestamp": timestamp,
        "step": step,
        "status": status,
        "details": details
    })


def main():
    st.title("arXiv Author Extractor")
    st.write(
        "Extract author and affiliation information from arXiv papers using Gemini AI and match affiliations to ROR IDs")

    with st.sidebar:
        st.header("Configuration")
        api_key = load_api_key()
        if not api_key:
            st.warning("No API key found in environment variables.")
            st.session_state.api_key = st.text_input(
                "Enter Gemini API Key",
                type="password",
                help="Enter your Gemini API key. This will be stored in session state."
            )
            if st.session_state.api_key:
                st.success("API key set for this session!")
        else:
            st.success("API key found!")

        model_choice = st.selectbox(
            "Select Gemini Model",
            options=["8b", "flash", "pro"],
            help="Choose the Gemini model to use for processing"
        )

        ror_strategy = st.selectbox(
            "ROR Matching Strategy",
            options=["single", "multi"],
            help="Choose the strategy for matching affiliations to ROR IDs"
        )

        input_method = st.radio(
            "Input Method",
            options=["DOI/arXiv ID", "Upload PDF"],
            help="Choose how to provide the paper"
        )

    col1, col2 = st.columns([2, 3])
    with col1:
        st.header("Input")

        if input_method == "DOI/arXiv ID":
            doi_input = st.text_input(
                "Enter DOI or arXiv ID",
                help="Enter the DOI (10.48550/arXiv.XXXX.XXXXX) or arXiv ID (XXXX.XXXXX)"
            )
        else:
            uploaded_file = st.file_uploader(
                "Upload PDF file",
                type=['pdf'],
                help="Upload a PDF file directly"
            )

        process_button = st.button(
            "Process Paper",
            type="primary",
            disabled=not (load_api_key() and (
                doi_input if input_method == "DOI/arXiv ID" else uploaded_file))
        )

    with col2:
        if process_button:
            try:
                retriever = ArxivPDFRetriever()
                processor = GeminiProcessor(
                    api_key=load_api_key(), model_choice=model_choice)
                matcher = RORMatcher(strategy=ror_strategy)

                with st.spinner("Processing paper..."):
                    if input_method == "DOI/arXiv ID":
                        add_to_history(
                            "Input", "Processing", f"Processing DOI/ID: {doi_input}")
                        success, pdf_content = retriever.download_pdf(
                            doi_input)
                        if not success:
                            st.error("Failed to download PDF")
                            add_to_history(
                                "Download", "Failed", retriever.get_download_status().message)
                            return

                        arxiv_id = retriever.extract_arxiv_id(doi_input)

                    else:
                        if not uploaded_file:
                            st.error("Please upload a PDF file")
                            return
                        pdf_path = save_uploaded_file(uploaded_file)
                        if not pdf_path:
                            return
                        with open(pdf_path, 'rb') as f:
                            pdf_content = f.read()
                        add_to_history(
                            "Input", "Processing", f"Processing uploaded file: {uploaded_file.name}")
                        arxiv_id = os.path.splitext(uploaded_file.name)[0]

                    with PDFImageConverter() as converter:
                        image = converter.convert_to_image(pdf_content)
                        if not image:
                            st.error("Failed to convert PDF to image")
                            add_to_history(
                                "Conversion", "Failed", converter.get_conversion_status().message)
                            return

                        temp_image_path = Path(tempfile.mktemp(suffix='.png'))
                        converter.save_image(image, temp_image_path)

                        try:
                            result = processor.process_image(temp_image_path)
                            if not result:
                                st.error("Failed to process image with Gemini")
                                add_to_history(
                                    "Processing", "Failed", processor.get_processing_status().message)
                                return

                            result["id"] = arxiv_id
                            result["doi"] = f"10.48550/arXiv.{arxiv_id}"

                            with st.spinner("Matching affiliations to ROR IDs..."):
                                enhanced_result = matcher.match_affiliations(
                                    result)
                                if not enhanced_result:
                                    st.warning(
                                        "Failed to match some affiliations to ROR IDs")
                                    add_to_history(
                                        "ROR Matching", "Partial", matcher.get_matching_status().message)
                                    enhanced_result = result
                                else:
                                    add_to_history(
                                        "ROR Matching", "Success", "Successfully matched affiliations to ROR IDs")

                            st.header("Results")
                            display_enhanced_results(enhanced_result)

                        finally:
                            if temp_image_path.exists():
                                temp_image_path.unlink()
                            if 'pdf_path' in locals() and pdf_path.exists():
                                pdf_path.unlink()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                add_to_history("Processing", "Error", str(e))

    with st.sidebar:
        st.header("Processing History")
        for entry in reversed(st.session_state.processing_history):
            with st.expander(f"{entry['step']} - {entry['timestamp']}", expanded=False):
                st.write(f"Status: {entry['status']}")
                st.write(f"Details: {entry['details']}")


if __name__ == "__main__":
    main()
