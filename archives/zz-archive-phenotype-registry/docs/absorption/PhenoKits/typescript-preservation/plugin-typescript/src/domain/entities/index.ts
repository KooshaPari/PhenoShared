// Domain entities - core business objects
import { DomainError } from '../errors/index.js';

export interface Entity {
  readonly id: string;
  readonly createdAt: Date;
  readonly updatedAt: Date;
}

export interface Example extends Entity {
  readonly name: string;
  readonly description?: string;
  readonly active: boolean;
}

export function createExample(name: string, description?: string): Example {
  if (!name || name.trim().length === 0) {
    throw DomainError.validation('name', 'Name is required');
  }
  if (name.length > 100) {
    throw DomainError.validation('name', 'Name must be less than 100 characters');
  }

  const now = new Date();
  return {
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now,
    name: name.trim(),
    description: description?.trim(),
    active: true,
  };
}

export function validateExample(example: Example): DomainError | null {
  if (!example.name || example.name.trim().length === 0) {
    return DomainError.validation('name', 'Name is required');
  }
  if (example.name.length > 100) {
    return DomainError.validation('name', 'Name must be less than 100 characters');
  }
  return null;
}
