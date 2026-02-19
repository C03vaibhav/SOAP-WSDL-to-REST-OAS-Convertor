import os
import shutil

BASE_DIR = "schema_registry"

def save_schema_files(department, service, version, wsdl, xsds):
    path = f"{BASE_DIR}/{department}/{service}/{version}"
    os.makedirs(path, exist_ok=True)

    wsdl_path = os.path.join(path, wsdl.filename)
    with open(wsdl_path, "wb") as f:
        shutil.copyfileobj(wsdl.file, f)

    xsd_names = []
    for xsd in xsds:
        xsd_path = os.path.join(path, xsd.filename)
        with open(xsd_path, "wb") as f:
            shutil.copyfileobj(xsd.file, f)
        xsd_names.append(xsd.filename)
    
    return path, xsd_names