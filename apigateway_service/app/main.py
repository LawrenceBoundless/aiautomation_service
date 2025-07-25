# apigateway_service/app/main.py
import os
import json
import httpx
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException, Security, Depends, File, UploadFile, Form
from fastapi.security.api_key import APIKeyHeader
from typing import List
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

# --- Load Credentials & Config from Environment Variables ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
PDF_READER_SERVICE_URL = os.environ.get("PDF_READER_SERVICE_URL")
API_KEY = os.environ.get("API_KEY")
API_KEY_NAME = "x-api-key"

# --- Initialize Clients and Security ---
slack_client = WebClient(token=SLACK_BOT_TOKEN)
signature_verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

app = FastAPI(title="API Gateway Service")

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

async def call_pdf_reader_and_notify(file_id: str, channel_id: str, user_id: str):
    """
    Background task to download a file, call the pdf-reader-service, and notify Slack.
    """
    try:
        file_info = slack_client.files_info(file=file_id).data['file']
        file_url = file_info['url_private']
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            file_response = await client.get(
                url=file_url, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
            )
            file_content = file_response.content
            filename = file_info.get("name", "uploaded_file.pdf")

            files = {'file': (filename, file_content, 'application/pdf')}
            data = {'checks_to_run': 'all'}
            
            # This is the secure, internal call to the worker microservice
            worker_response = await client.post(
                f"{PDF_READER_SERVICE_URL}/run-programmatic-checks/", files=files, data=data
            )
            worker_response.raise_for_status()
            results = worker_response.json()
            all_errors = results.get("programmatic_errors", [])

        if all_errors:
            error_list = "\n".join([f"• {error}" for error in all_errors])
            message = f"Hi <@{user_id}>! I found some issues in `{filename}`:\n\n{error_list}"
        else:
            message = f"Hi <@{user_id}>! ✅ I've reviewed `{filename}` and found no programmatic errors."
        
        slack_client.chat_postMessage(channel=channel_id, text=message)

    except Exception as e:
        slack_client.chat_postMessage(channel=channel_id, text=f"Sorry, an error occurred: {e}")


@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    if not signature_verifier.is_valid_request(await request.body(), request.headers):
        raise HTTPException(status_code=403, detail="Invalid request signature")

    form_data = await request.form()
    payload_str = form_data.get("payload")

    if not payload_str:
        subcommand = form_data.get("text", "").strip()
        trigger_id = form_data.get("trigger_id")
        
        if subcommand == "pdf":
            slack_client.views_open(trigger_id=trigger_id, view={
                "type": "modal", "callback_id": "pdf_check_modal",
                "title": {"type": "plain_text", "text": "Check a PDF"},
                "submit": {"type": "plain_text", "text": "Run Checks"},
                "blocks": [{"type": "input", "block_id": "pdf_file_block", "label": {"type": "plain_text", "text": "Upload PDF File"}, "element": {"type": "file_input", "action_id": "pdf_file_input", "filetypes": ["pdf"]}}]
            })
        else:
            slack_client.chat_postMessage(channel=form_data.get("user_id"), text="Unknown command. Try `/aiauto pdf`.")
        
        return Response(status_code=200)

    payload = json.loads(payload_str)
    if payload.get("type") == "view_submission":
        if payload.get("view", {}).get("callback_id") == "pdf_check_modal":
            values = payload['view']['state']['values']
            file_id = values['pdf_file_block']['pdf_file_input']['files'][0]['id']
            user_id = payload['user']['id']
            background_tasks.add_task(call_pdf_reader_and_notify, file_id, user_id, user_id)
            return Response(status_code=200)

    return Response(status_code=400, content="Unsupported event")


@app.post("/api/v1/run-checks")
async def api_run_checks(
    checks_to_run: List[str] = Form(...),
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key)
):
    try:
        file_content = await file.read()
        filename = file.filename

        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {'file': (filename, file_content, 'application/pdf')}
            data = {'checks_to_run': checks_to_run}
            
            worker_response = await client.post(
                f"{PDF_READER_SERVICE_URL}/run-programmatic-checks/", files=files, data=data
            )
            worker_response.raise_for_status()
            return worker_response.json()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))