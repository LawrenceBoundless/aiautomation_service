# app/verifier.py
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
    """
    Analyzes the extracted document text using Gemini Pro.
    Assumes you have authenticated with GCP CLI (`gcloud auth application-default login`).
    """
    # Configure the Gemini API
    # Replace 'your-gcp-project-id' with your actual project ID
    # and 'your-region' with your GCP region (e.g., 'us-central1')
    genai.configure(
        project_id='your-gcp-project-id',
        location='your-region',
    )
    
    model = genai.GenerativeModel('gemini-1.5-pro-preview-0409')

    full_prompt = f"{prompt}\n\n---DOCUMENT TEXT---\n{document_text}"

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Error during Gemini API call: {e}"