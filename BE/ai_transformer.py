import os
from dotenv import load_dotenv

OAS_BASE_DIR = "OAS_registry"

def get_genai_client():
    load_dotenv()
    from google import genai
    return genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

async def ai_generate_rest(wsdl_content, xsd_content, soap_xml, mode="transform", service="", version=""):
    client = get_genai_client()
    
    if mode == "transform":
        system_msg = "You are a Senior API Architect. Output only JSON."
        prompt = f"Convert SOAP to REST JSON.\nWSDL: {wsdl_content}\nXSD: {xsd_content}\nRequest: {soap_xml}"
    else:
        system_msg = "You are a Senior API Architect. Output only OpenAPI 3.x YAML."
        prompt = f"Generate OAS 3.x YAML for service {service} v{version}.\nWSDL: {wsdl_content}\nXSDs: {xsd_content}"

    chat = client.chats.create(
        model="gemma-3-27b-it",
        history=[{"role": "user", "parts": [{"text": system_msg}]}]
    )
    response = chat.send_message(prompt)
    return response.text.replace("```yaml", "").replace("```json", "").replace("```", "").strip()

def save_oas_spec(department, service, version, content):
    path = f"{OAS_BASE_DIR}/{department}/{service}/{version}"
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, "openapi.yaml")
    with open(file_path, "w") as f:
        f.write(content)
    return file_path