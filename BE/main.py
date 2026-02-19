from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
import os
import shutil
import sys
import uvicorn
from dotenv import load_dotenv

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

app = FastAPI(
    title="SOAP Schema Registry & Validator",
    description="Strict WSDL/XSD based SOAP validation service",
    version="1.0.0"
)

BASE_DIR = "schema_registry"

# ---------------------------------------------------------
# Utility: Resolve WSDL path dynamically
# ---------------------------------------------------------
def resolve_wsdl_path(department: str, service: str, version: str) -> str:
    base_path = f"{BASE_DIR}/{department}/{service}/{version}"

    if not os.path.exists(base_path):
        raise HTTPException(
            status_code=404,
            detail=f"Schema not found for {department}/{service}/{version}"
        )

    for file in os.listdir(base_path):
        if file.endswith(".wsdl"):
            return os.path.join(base_path, file)

    raise HTTPException(
        status_code=404,
        detail="WSDL file not found in schema registry"
    )

# ---------------------------------------------------------
# Upload WSDL + XSDs
# ---------------------------------------------------------
@app.post("/upload/wsdl")
async def upload_wsdl(
    department: str = Form(...),
    service: str = Form(...),
    version: str = Form(...),
    wsdl: UploadFile = File(...),
    xsds: List[UploadFile] = File(...)
):
    path = f"{BASE_DIR}/{department}/{service}/{version}"
    os.makedirs(path, exist_ok=True)

    wsdl_path = os.path.join(path, wsdl.filename)
    with open(wsdl_path, "wb") as f:
        shutil.copyfileobj(wsdl.file, f)

    xsd_files = []
    for xsd in xsds:
        xsd_path = os.path.join(path, xsd.filename)
        with open(xsd_path, "wb") as f:
            shutil.copyfileobj(xsd.file, f)
        xsd_files.append(xsd.filename)

    return {
        "status": "Uploaded successfully",
        "stored_at": path,
        "xsd_files": xsd_files
    }

# ---------------------------------------------------------
# Validate SOAP Request
# ---------------------------------------------------------
@app.post("/validate")
async def validate_soap(
    department: str,
    service: str,
    version: str,
    soap_xml: UploadFile = File(...)
):
    # MOVED IMPORT HERE: Fixes Windows Reload Crash
    from BE.generic_soap_validator import GenericSoapValidator
    
    wsdl_path = resolve_wsdl_path(department, service, version)
    validator = GenericSoapValidator(wsdl_path)
    soap_data = (await soap_xml.read()).decode("utf-8")

    try:
        validator.validate(soap_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "VALID", "service": service}

# ---------------------------------------------------------
# LLM Transformation
# ---------------------------------------------------------
def get_genai_client():
    load_dotenv()
    # MOVED IMPORT HERE: Fixes Windows Reload Crash
    from google import genai
    api_key = os.getenv("GOOGLE_API_KEY")
    return genai.Client(api_key=api_key)

@app.post("/transform")
async def transform_soap_to_rest(
    department: str = Form(...),  # Explicit Form(...) fixes 422 error
    service: str = Form(...),     # Explicit Form(...) fixes 422 error
    version: str = Form(...),     # Explicit Form(...) fixes 422 error
    soap_xml: str = Form(...) 
):
    wsdl_path = resolve_wsdl_path(department, service, version)
    wsdl_dir = os.path.dirname(wsdl_path)
    xsd_files = [f for f in os.listdir(wsdl_dir) if f.endswith('.xsd')]
    
    if not xsd_files:
        raise HTTPException(status_code=404, detail="No XSD found")
    
    xsd_path = os.path.join(wsdl_dir, xsd_files[0])

    with open(wsdl_path, "r") as f: wsdl_content = f.read()
    with open(xsd_path, "r") as f: xsd_content = f.read()

    prompt = f"""
    Task: Convert the provided SOAP Request into its modern RESTful JSON equivalent.
    WSDL Definition: {wsdl_content}
    XSD Schema: {xsd_content}
    Incoming SOAP Request: {soap_xml}
    
    Output: Return ONLY a valid JSON object with 'endpoint_info' and 'payload'.
    """

    try:
        client = get_genai_client()
        chat = client.chats.create(
            model="gemma-3-27b-it",
            history=[
                {"role": "user", "parts": [{"text": "You are a Senior API Architect. Output only JSON."}]},
                {"role": "model", "parts": [{"text": "Understood. I will provide only JSON mappings."}]}
            ]
        )
        response = chat.send_message(prompt)
        return {"rest_json": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GenAI Error: {str(e)}")

# ---------------------------------------------------------
# Runner
# ---------------------------------------------------------
if __name__ == "__main__":
    # FORCE UTF-8: Fixes the cp1252 decoding error on Windows
    os.environ["PYTHONUTF8"] = "1"
    
    # Use string "main:app" for reliable reloading
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, log_level="debug")