import Ajv from 'ajv';
import * as yaml from 'js-yaml';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export class JsonSchemaValidator {
  private ajv: Ajv;
  private schemas: Map<string, object>;

  constructor() {
    this.ajv = new Ajv();
    this.schemas = new Map();
  }

  validate(schema: string, document: string): ValidationResult {
    try {
      const schemaObj = JSON.parse(schema);
      const documentObj = JSON.parse(document);
      
      const validate = this.ajv.compile(schemaObj);
      const valid = validate(documentObj);
      
      if (valid) {
        return { isValid: true, errors: [], warnings: [] };
      }
      
      const errors = validate.errors?.map(e => 
        `[${e.instancePath}] ${e.message}`
      ) || [];
      
      return { isValid: false, errors, warnings: [] };
    } catch (e) {
      return { 
        isValid: false, 
        errors: [(e as Error).message], 
        warnings: [] 
      };
    }
  }

  addSchema(name: string, schemaContent: string): void {
    this.schemas.set(name, JSON.parse(schemaContent));
  }

  validateAgainstNamedSchema(document: string, schemaName: string): ValidationResult {
    const schema = this.schemas.get(schemaName);
    if (!schema) {
      return { 
        isValid: false, 
        errors: [`Schema '${schemaName}' not found`], 
        warnings: [] 
      };
    }
    return this.validate(JSON.stringify(schema), document);
  }
}

export class YamlValidator {
  private jsonValidator: JsonSchemaValidator;

  constructor(jsonValidator?: JsonSchemaValidator) {
    this.jsonValidator = jsonValidator || new JsonSchemaValidator();
  }

  validate(schema: string, document: string): ValidationResult {
    try {
      const yamlObj = yaml.load(document);
      const jsonStr = JSON.stringify(yamlObj);
      return this.jsonValidator.validate(schema, jsonStr);
    } catch (e) {
      return { 
        isValid: false, 
        errors: [`Invalid YAML: ${(e as Error).message}`], 
        warnings: [] 
      };
    }
  }

  addSchema(name: string, schemaContent: string): void {
    this.jsonValidator.addSchema(name, schemaContent);
  }
}
