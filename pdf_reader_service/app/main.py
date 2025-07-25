from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from typing import List
import fitz  # PyMuPDF
from . import verifier
from . import checks

app = FastAPI(
    title="PDF Verification Service",
    description="A service to run programmatic and AI-based checks on PDF documents.",
)

# A mapping from string names to the actual check functions
AVAILABLE_CHECKS = {
    "edition_dates": checks.check_edition_dates,
    "signature_format": checks.check_signature_date_format,
    "signature_recency": checks.check_signature_date_recency,
    "preparer_jeffrey_hales": checks.check_preparer_jeffrey_hales,
    "missing_pages": checks.check_missing_pages,
    "a_number_consistency": checks.check_a_number_consistency,
    "form_i131_box_3a": checks.check_form_i131_box_3a,
}

@app.post("/run-programmatic-checks/")
async def run_programmatic_checks(
    checks_to_run: List[str] = Form(...), 
    file: UploadFile = File(...)
):
    """
    Accepts a PDF file and a list of programmatic checks to run.
    To run all available checks, send "all" as a value.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_content = await file.read()
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        all_errors = []

        # If "all" is specified, run every check.
        if "all" in checks_to_run:
            for check_function in AVAILABLE_CHECKS.values():
                errors = check_function(doc)
                all_errors.extend(errors)
        else:
            # Otherwise, run only the specified checks.
            for check_name in checks_to_run:
                if check_name in AVAILABLE_CHECKS:
                    errors = AVAILABLE_CHECKS[check_name](doc)
                    all_errors.extend(errors)
                else:
                    all_errors.append(f"Warning: Unknown check '{check_name}' requested.")
        
        doc.close()
        return {"filename": file.filename, "programmatic_errors": all_errors}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.post("/run-ai-analysis/")
async def run_ai_analysis(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts a PDF file and a prompt for AI-based analysis.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_content = await file.read()
        
        document_text = verifier.extract_text_from_pdf(pdf_content)
        if not document_text:
            raise HTTPException(status_code=500, detail="Failed to extract text from PDF.")

        analysis_result = verifier.analyze_document_with_gemini(document_text, prompt)

        return {"filename": file.filename, "analysis_result": analysis_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")