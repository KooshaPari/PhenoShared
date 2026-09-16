/**
 * EntityId - Unique identifier with namespace
 * Mirrors: phenotype-core Rust / pheno_core Python
 */
export interface EntityId {
  id: string;
  namespace: string;
}

export class Entity implements EntityId {
  constructor(
    public id: string,
    public namespace: string
  ) {
    this.validate();
  }

  private validate(): void {
    if (!this.id || this.id.length === 0) {
      throw new Error('EntityId.id cannot be empty');
    }
    if (!this.namespace || this.namespace.length === 0) {
      throw new Error('EntityId.namespace cannot be empty');
    }
  }

  toJSON(): string {
    return JSON.stringify({ id: this.id, namespace: this.namespace });
  }

  static fromJSON(json: string): Entity {
    const parsed = JSON.parse(json) as EntityId;
    return new Entity(parsed.id, parsed.namespace);
  }

  toString(): string {
    return `${this.namespace}:${this.id}`;
  }
}

/**
 * ValidationResult - Result of validation operation
 */
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validate an entity ID
 */
export function validateEntity(entity: EntityId): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!entity.id || entity.id.length === 0) {
    errors.push('EntityId.id is required');
  }
  if (!entity.namespace || entity.namespace.length === 0) {
    errors.push('EntityId.namespace is required');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Generate a unique entity ID
 */
export function generateId(namespace: string): Entity {
  const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  return new Entity(id, namespace);
}
