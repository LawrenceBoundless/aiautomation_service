import os
import fitz  # PyMuPDF
import vertexai
from vertexai.generative_models import GenerativeModel

def extract_text_from_pdf(pdf_file: bytes) -> str:
    """Extracts all text from a PDF file for AI analysis."""
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
    """Analyzes the extracted document text using the Vertex AI Gemini Pro model."""

    project_id = os.environ.get('GCP_PROJECT_ID')
    location = os.environ.get('GCP_LOCATION')

    if not project_id or not location:
        error_message = "Error: GCP_PROJECT_ID and GCP_LOCATION environment variables are not set."
        print(error_message)
        return error_message

    try:
        # Initialize the Vertex AI client
        vertexai.init(project=project_id, location=location)

        # NOTE: Replace with a model name confirmed to be available in your project/region
        # You can find this by running `gcloud ai models list --region=[your-region]`
        model = GenerativeModel("gemini-1.5-pro-preview-0409") 

        full_prompt = f"{prompt}\n\n---DOCUMENT TEXT---\n{document_text}"

        # Generate content
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        error_message = f"Error during Vertex AI API call: {e}"
        print(error_message)
        return error_message