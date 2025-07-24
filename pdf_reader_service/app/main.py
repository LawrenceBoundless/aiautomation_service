# app/main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from . import verifier

app = FastAPI(
    title="PDF Reader Service",
    description="Extracts text from a PDF and uses AI to verify its contents.",
)

@app.post("/verify-pdf/")
async def verify_pdf(
    prompt: str = Form(...), 
    file: UploadFile = File(...)
):
    """
    Accepts a PDF file and a verification prompt.
    - Extracts text from the PDF.
    - Uses the provided prompt to have an AI model analyze the text.
    - Returns the AI's analysis.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    try:
        pdf_content = await file.read()
        
        # 1. Extract text from the PDF
        document_text = verifier.extract_text_from_pdf(pdf_content)
        if not document_text:
            raise HTTPException(status_code=500, detail="Failed to extract text from PDF.")

        # 2. Analyze the text with the AI model
        analysis_result = verifier.analyze_document_with_gemini(document_text, prompt)

        return {"filename": file.filename, "analysis_result": analysis_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")