import os
import fitz  # PyMuPDF
import google.generativeai as genai

def extract_text_from_pdf(pdf_file: bytes) -> str:
    """Extracts all text from a PDF file."""
    try:
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def analyze_document_with_gemini(document_text: str, prompt: str) -> str:
    """Analyzes the extracted document text using Gemini Pro."""

    # Get configuration from environment variables set by Cloud Run
    project_id = os.environ.get('GCP_PROJECT_ID')
    location = os.environ.get('GCP_LOCATION')

    if not project_id or not location:
        error_message = "Error: GCP_PROJECT_ID and GCP_LOCATION environment variables are not set."
        print(error_message)
        return error_message

    try:

        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-pro-preview-0409')

        full_prompt = f"{prompt}\n\n---DOCUMENT TEXT---\n{document_text}"

        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        error_message = f"Error during Gemini API call: {e}"
        print(error_message)
        return error_message