import os
import logging
import multiprocessing
from typing import Optional, List
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# --- Local Utils Imports ---
# from utils.sos import sos # Removed SMS feature
from utils.database import get_or_create_user, save_evidence_metadata
# from utils.database import update_user_contacts # Removed contacts management
from utils.storage import upload_evidence_to_cloudinary
from utils.chatbot import WomenSafetyChatbot


# -----------------------------
# ENV + APP SETUP
# -----------------------------
load_dotenv()

app = FastAPI(title="VoiceGuard Safety API", version="2.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# Ensure the temporary upload folder exists
UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------------
# GLOBAL STATE FOR PROCESS MANAGEMENT
# -----------------------------
monitoring_process: Optional[multiprocessing.Process] = None
stop_monitoring_event: Optional[multiprocessing.Event] = None

# -----------------------------
# REQUEST MODELS
# -----------------------------
class MonitoringRequest(BaseModel):
    user_id: str

class ContactRequest(BaseModel):
    user_id: str
    contact: str

class SosRequest(BaseModel):
    user_id: str

# -----------------------------
# API ROUTES
# -----------------------------

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "VoiceGuard API is running."}

# User contact management and SOS removed as requested.


# Background monitoring moved to client-side.

# -----------------------------
# EVIDENCE LOCKER
# -----------------------------
@app.post("/upload_evidence")
async def upload_evidence_route(user_id: str = Form(...), files: List[UploadFile] = File(...)):

    user = get_or_create_user(user_id)
    if not user:
        raise HTTPException(status_code=500, detail="Could not get or create user.")

    successful_uploads = []
    failed_uploads = []

    for file in files:
        original_filename = file.filename
        temp_file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}-{original_filename}")
        
        try:
            # 1. Save file temporarily to the server
            with open(temp_file_path, "wb") as buffer:
                buffer.write(await file.read())
            logging.info(f"Temporarily saved file: {temp_file_path}")

            # 2. Upload the temporary file to Cloudinary
            upload_result = upload_evidence_to_cloudinary(
                file_path=temp_file_path,
                user_id=user_id,
                file_name=original_filename
            )
            
            if upload_result and 'secure_url' in upload_result:
                # 3. Save metadata to MongoDB
                save_evidence_metadata(
                    user_id=user_id,
                    filename=original_filename,
                    file_url=upload_result['secure_url'],
                    content_type=file.content_type
                )
                successful_uploads.append(original_filename)
                logging.info(f"Successfully uploaded and logged evidence: {original_filename} for user {user_id}")
            else:
                failed_uploads.append(original_filename)
                logging.error(f"Cloudinary upload failed for {original_filename}.")

        except Exception as e:
            logging.error(f"Error processing file {original_filename}: {e}")
            failed_uploads.append(original_filename)
        finally:
            # 4. Delete the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logging.info(f"Deleted temporary file: {temp_file_path}")

    if not successful_uploads:
        raise HTTPException(status_code=500, detail="File upload failed for all files.")

    return {
        'status': 'success',
        'message': f'Successfully uploaded {len(successful_uploads)} file(s).',
        'successful_files': successful_uploads,
        'failed_files': failed_uploads
    }


# -----------------------------
# CHATBOT INSTANCE & ROUTES
# -----------------------------
# Prioritize Google Gemini API Key
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
chatbot_instance = WomenSafetyChatbot(api_key=API_KEY)

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ClearHistoryRequest(BaseModel):
    user_id: str

@app.post('/chat')
async def chat_route(data: ChatRequest):

    user = get_or_create_user(data.user_id)
    if not user:
        raise HTTPException(status_code=500, detail="Could not get or create user.")

    try:
        response = chatbot_instance.chat(data.user_id, data.message)
        if not response.get('success'):
            raise HTTPException(status_code=400, detail=response)
        return response
    except Exception as e:
        logging.error(f"Error in /chat route: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/stats')
async def stats_route():
    stats = chatbot_instance.get_stats()
    return stats

@app.post('/clear-history')
async def clear_history_route(data: ClearHistoryRequest):
    chatbot_instance.clear_user_history(data.user_id)
    return {'success': True, 'message': 'History cleared'}


# -----------------------------
# MAIN ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    # Required for multiprocessing to work correctly on some platforms
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
