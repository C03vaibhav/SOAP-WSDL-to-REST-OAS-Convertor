import streamlit as st
import requests

# Configure the FastAPI endpoint
BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="SOAP Validator & Transformer", layout="wide")

st.title("SOAP Schema Registry & Validator")
st.markdown("---")

# Sidebar for common inputs
st.sidebar.header("Service Context")
dept = st.sidebar.text_input("Department", value="finance")
service = st.sidebar.text_input("Service Name", value="customer")
version = st.sidebar.text_input("Version", value="v1")

# Tabs for different operations
tab1, tab2, tab3 = st.tabs(["Upload Schema", "Validate SOAP", "REST Convertor"])

# ---------------------------------------------------------
# TAB 1: UPLOAD WSDL & XSD
# ---------------------------------------------------------
with tab1:
    st.header("Upload Service Definition")
    
    col1, col2 = st.columns(2)
    with col1:
        wsdl_file = st.file_uploader("Select WSDL File", type=['wsdl', 'xml'])
    with col2:
        xsd_files = st.file_uploader("Select XSD Files", type=['xsd'], accept_multiple_files=True)

    # Action Buttons
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Register Schema", use_container_width=True):
            if wsdl_file and xsd_files:
                files = [('wsdl', (wsdl_file.name, wsdl_file.getvalue(), 'application/octet-stream'))]
                for xsd in xsd_files:
                    files.append(('xsds', (xsd.name, xsd.getvalue(), 'application/octet-stream')))
                
                data = {"department": dept, "service": service, "version": version}
                
                with st.spinner("Uploading to Schema Registry..."):
                    response = requests.post(f"{BASE_URL}/upload/wsdl", data=data, files=files)
                    
                if response.status_code == 200:
                    st.success("Schema registered successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Upload failed: {response.text}")
            else:
                st.warning("Please provide both a WSDL and at least one XSD file.")

    with col_btn2:
        if st.button("Generate OAS 3.x Spec", use_container_width=True):
            if dept and service and version:
                payload = {"department": dept, "service": service, "version": version}
                
                with st.spinner("AI is analyzing WSDL/XSD to generate OpenAPI Spec..."):
                    response = requests.post(f"{BASE_URL}/generate-oas", data=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"OAS 3.x generated! Stored in: {result['saved_at']}")
                    
                    # Provide a Download Button for the generated YAML
                    st.download_button(
                        label="Download openapi.yaml",
                        data=result['oas_content'],
                        file_name=f"{service}_openapi.yaml",
                        mime="text/yaml"
                    )
                    
                    # Preview the result
                    with st.expander("View Generated Specification"):
                        st.code(result['oas_content'], language="yaml")
                else:
                    st.error(f"Generation failed: {response.text}")
            else:
                st.warning("Please ensure Department, Service, and Version are filled in the sidebar.")

# ---------------------------------------------------------
# TAB 2: VALIDATE SOAP REQUEST
# ---------------------------------------------------------
with tab2:
    st.header("Validate SOAP XML")
    
    soap_input_type = st.radio("Input Method", ["File Upload", "Paste XML"])
    
    soap_xml_data = None
    if soap_input_type == "File Upload":
        uploaded_soap = st.file_uploader("Upload SOAP Request", type=['xml'], key="Validate SOAP")
        if uploaded_soap:
            soap_xml_data = uploaded_soap.getvalue()
    else:
        soap_xml_data = st.text_area("Paste SOAP XML here", height=300)

    if st.button("Validate Request"):
        if soap_xml_data:
            # Prepare file for upload
            files = {'soap_xml': ('request.xml', soap_xml_data, 'text/xml')}
            params = {
                "department": dept,
                "service": service,
                "version": version
            }
            
            with st.spinner("Validating against WSDL/XSD..."):
                # Note: Passing params in URL because FastAPI @app.post handles them as query/form
                response = requests.post(f"{BASE_URL}/validate", params=params, files=files)
            
            if response.status_code == 200:
                st.balloons()
                st.success("SOAP Request is VALID")
                st.json(response.json())
            else:
                st.error("Validation Failed")
                st.code(response.json().get("detail", "Unknown Error"), language="text")
        else:
            st.warning("Please provide SOAP XML data.")
            
# ---------------------------------------------------------
# TAB 3: LLM TRANSFORMATION
# ---------------------------------------------------------
with tab3:
    st.header("AI SOAP-to-REST Transformer")
    st.info("This uses an LLM to map your SOAP XML to a RESTful JSON payload based on the registered schema.")

    soap_to_transform = None
    if soap_input_type == "File Upload":
        uploaded_soap = st.file_uploader("Upload SOAP Request", type=['xml'], key="SOAP to REST through LLM")
        if uploaded_soap:
            soap_to_transform = uploaded_soap.getvalue()
    else:
        soap_to_transform = st.text_area("Paste SOAP XML here", height=300)

    if st.button("Generate REST Mapping"):
        if soap_to_transform:
            payload = {
                "department": dept,
                "service": service,
                "version": version,
                "soap_xml": soap_to_transform
            }
            
            with st.spinner("LLM is analyzing WSDL/XSD and mapping fields..."):
                # We use data= for Form fields in requests
                response = requests.post(f"{BASE_URL}/transform", data=payload)
            
            if response.status_code == 200:
                st.subheader("Converted REST Request")
                # Show the JSON output from the LLM
                st.markdown(response.json().get("rest_json"))
            else:
                st.error(f"Transformation failed: {response.text}")
        else:
            st.warning("Please paste a SOAP request first.")