import os
from fastapi import HTTPException

BASE_DIR = "schema_registry"

def resolve_wsdl_path(department: str, service: str, version: str) -> str:
    base_path = f"{BASE_DIR}/{department}/{service}/{version}"
    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail="Schema path not found")

    for file in os.listdir(base_path):
        if file.endswith(".wsdl"):
            return os.path.join(base_path, file)
    raise HTTPException(status_code=404, detail="WSDL file missing")