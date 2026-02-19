import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List
from schema_utils import resolve_wsdl_path
from file_manager import save_schema_files
from soap_handler import validate_soap_xml
from ai_transformer import ai_generate_rest, save_oas_spec

app = FastAPI(title="SOAP-to-REST Modular Service")

@app.post("/upload/wsdl")
async def upload(department: str = Form(...), service: str = Form(...), version: str = Form(...), 
                 wsdl: UploadFile = File(...), xsds: List[UploadFile] = File(...)):
    path, xsd_files = save_schema_files(department, service, version, wsdl, xsds)
    return {"status": "Uploaded", "path": path}

@app.post("/validate")
async def validate(department: str, service: str, version: str, soap_xml: UploadFile = File(...)):
    wsdl_path = resolve_wsdl_path(department, service, version)
    content = await soap_xml.read()
    try:
        validate_soap_xml(wsdl_path, content)
        return {"status": "VALID"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transform")
async def transform(department: str = Form(...), service: str = Form(...), version: str = Form(...), soap_xml: str = Form(...)):
    wsdl_path = resolve_wsdl_path(department, service, version)
    with open(wsdl_path, "r") as f: wsdl_c = f.read()
    # Simplified: grabbing first XSD
    xsd_path = os.path.join(os.path.dirname(wsdl_path), [f for f in os.listdir(os.path.dirname(wsdl_path)) if f.endswith('.xsd')][0])
    with open(xsd_path, "r") as f: xsd_c = f.read()
    
    result = await ai_generate_rest(wsdl_c, xsd_c, soap_xml, mode="transform")
    return {"rest_json": result}

@app.post("/generate-oas")
async def generate_oas(department: str = Form(...), service: str = Form(...), version: str = Form(...)):
    wsdl_path = resolve_wsdl_path(department, service, version)
    wsdl_dir = os.path.dirname(wsdl_path)
    with open(wsdl_path, "r") as f: wsdl_c = f.read()
    
    all_xsds = " ".join([open(os.path.join(wsdl_dir, f)).read() for f in os.listdir(wsdl_dir) if f.endswith('.xsd')])
    
    oas_content = await ai_generate_rest(wsdl_c, all_xsds, None, mode="oas", service=service, version=version)
    saved_path = save_oas_spec(department, service, version, oas_content)
    
    return {"status": "OAS Generated", "saved_at": saved_path, "oas_content": oas_content}

if __name__ == "__main__":
    os.environ["PYTHONUTF8"] = "1"
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)