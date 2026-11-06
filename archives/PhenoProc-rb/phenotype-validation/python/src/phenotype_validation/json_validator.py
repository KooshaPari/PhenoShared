"""JSON Schema validator using jsonschema library"""
import json
from typing import List, Dict, Any
import jsonschema

class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

class JsonSchemaValidator:
    """JSON Schema validator implementation"""
    
    def __init__(self):
        self._schemas: Dict[str, dict] = {}
    
    def validate(self, schema: str, document: str) -> ValidationResult:
        """Validate a JSON document against a schema"""
        errors = []
        
        try:
            schema_obj = json.loads(schema)
        except json.JSONDecodeError as e:
            return ValidationResult(False, [f"Invalid schema JSON: {e}"])
        
        try:
            document_obj = json.loads(document)
        except json.JSONDecodeError as e:
            return ValidationResult(False, [f"Invalid document JSON: {e}"])
        
        # Validate
        validator = jsonschema.Draft7Validator(schema_obj)
        validation_errors = list(validator.iter_errors(document_obj))
        
        if validation_errors:
            errors = [f"[{e.json_path}] {e.message}" for e in validation_errors]
            return ValidationResult(False, errors)
        
        return ValidationResult(True)
    
    def add_schema(self, name: str, schema_content: str) -> None:
        """Add a named schema to the cache"""
        self._schemas[name] = json.loads(schema_content)
    
    def validate_against_named_schema(self, document: str, schema_name: str) -> ValidationResult:
        """Validate against a cached schema"""
        if schema_name not in self._schemas:
            return ValidationResult(False, [f"Schema '{schema_name}' not found"])
        
        schema_json = json.dumps(self._schemas[schema_name])
        return self.validate(schema_json, document)
