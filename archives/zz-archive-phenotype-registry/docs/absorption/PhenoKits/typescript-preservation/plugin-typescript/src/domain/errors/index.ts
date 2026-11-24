// Domain errors - use discriminated unions for type safety
export class DomainError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly field?: string
  ) {
    super(message);
    this.name = 'DomainError';
  }

  static notFound(id: string): DomainError {
    return new DomainError(`Entity not found: ${id}`, 'NOT_FOUND');
  }

  static alreadyExists(id: string): DomainError {
    return new DomainError(`Entity already exists: ${id}`, 'ALREADY_EXISTS');
  }

  static validation(field: string, message: string): DomainError {
    return new DomainError(message, 'VALIDATION', field);
  }

  static concurrency(message: string): DomainError {
    return new DomainError(message, 'CONCURRENCY');
  }
}

export type Result<T> = { success: true; data: T } | { success: false; error: DomainError };
