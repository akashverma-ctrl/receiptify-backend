from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
import base64
import yaml

app = FastAPI()

# Enable CORS for frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load secrets from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "akashverma-ctrl"
REPO_NAME = "receiptify-data"   # <-- Better to keep master_data in separate repo
FILE_PATH = "registrations.yaml"

URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

@app.post("/register/")
async def register(
    student_name: str = Form(...),
    email: str = Form(...),
    transaction_id: str = Form(...),
):
    # Get file from GitHub
    response = requests.get(URL, headers=HEADERS)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info["sha"]
        content = base64.b64decode(file_info["content"]).decode("utf-8")
        data = yaml.safe_load(content) or []
    else:
        sha = None
        data = []

    # Prevent duplicate transaction_id
    for entry in data:
        if entry.get("transaction_id") == transaction_id:
            return {"error": True, "message": "Transaction already exists"}

    # Add new entry
    new_entry = {"student_name": student_name, "email": email, "transaction_id": transaction_id}
    data.append(new_entry)

    # Commit back to GitHub
    updated_content = yaml.safe_dump(data, sort_keys=False, indent=2)
    encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"chore: add registration {transaction_id}",
        "content": encoded_content,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha

    put_response = requests.put(URL, headers=HEADERS, json=payload)
    if put_response.status_code not in [200, 201]:
        return {"error": True, "details": put_response.json()}

    return {"success": True, "message": f"Registered {student_name} successfully"}
