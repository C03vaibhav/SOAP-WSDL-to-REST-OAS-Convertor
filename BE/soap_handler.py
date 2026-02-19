from lxml import etree
from zeep import Client
from zeep.transports import Transport
from zeep.settings import Settings
import os

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"


class SoapValidationError(Exception):
    pass


class GenericSoapValidator:

    def __init__(self, wsdl_path: str):
        if not os.path.exists(wsdl_path):
            raise FileNotFoundError("WSDL not found")

        self.wsdl_path = wsdl_path

        self.client = Client(
            wsdl=wsdl_path,
            transport=Transport(),
            settings=Settings(strict=True)
        )

    def validate(self, soap_xml: str):
        """
        Validates SOAP request against WSDL + XSD strictly
        """
        # 1️⃣ Parse SOAP XML
        try:
            soap_doc = etree.fromstring(soap_xml.encode())
        except Exception as e:
            raise SoapValidationError(f"Invalid XML: {e}")

        # 2️⃣ Extract SOAP Body
        body = soap_doc.find(f"{{{SOAP_NS}}}Body")
        if body is None or len(body) == 0:
            raise SoapValidationError("SOAP Body is missing")

        request_element = body[0]

        # 3️⃣ Determine operation name
        operation_name = etree.QName(request_element).localname

        if operation_name not in self._get_operations():
            raise SoapValidationError(
                f"Operation '{operation_name}' not defined in WSDL"
            )

        # 4️⃣ Load schema(s)
        schema = self._load_combined_schema()

        # 5️⃣ XSD validation
        try:
            schema.assertValid(request_element)
        except etree.DocumentInvalid as e:
            raise SoapValidationError(f"XSD validation failed: {e}")

        return True

    def _get_operations(self):
        """
        Reads operations from WSDL
        """
        operations = set()
        for service in self.client.wsdl.services.values():
            for port in service.ports.values():
                for op in port.binding._operations:
                    operations.add(op)
        return operations

    def _load_combined_schema(self):
        """
        Loads all XSDs referenced by WSDL
        """
        schemas = []

        wsdl_dir = os.path.dirname(self.wsdl_path)

        for root, _, files in os.walk(wsdl_dir):
            for file in files:
                if file.endswith(".xsd"):
                    with open(os.path.join(root, file), "rb") as f:
                        schemas.append(etree.XML(f.read()))

        if not schemas:
            raise SoapValidationError("No XSD files found")

        schema_doc = etree.XML(
            b"<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'></xs:schema>"
        )

        for s in schemas:
            schema_doc.append(s)

        return etree.XMLSchema(schema_doc)


def validate_soap_xml(wsdl_path: str, soap_xml_bytes: bytes):
    validator = GenericSoapValidator(wsdl_path)
    soap_data = soap_xml_bytes.decode("utf-8")
    validator.validate(soap_data)
    return True