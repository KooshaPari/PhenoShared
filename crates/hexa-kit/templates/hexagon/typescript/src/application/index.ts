/**
 * Application Layer - Use cases and DTOs
 */

import { InputPort } from '../ports';

// Use Case
export interface UseCase<I, O> extends InputPort {
  execute(input: I): Promise<O>;
}

export type CommandUseCase<C, R> = UseCase<C, R>;
export type QueryUseCase<Q, R> = UseCase<Q, R>;

// Use Case Function Adapter
export class UseCaseFunc<I, O> implements UseCase<I, O> {
  constructor(
    private readonly fn: (input: I) => Promise<O>,
  ) {}

  async execute(input: I): Promise<O> {
    return this.fn(input);
  }
}

export class CommandFunc<C, R> implements CommandUseCase<C, R> {
  constructor(
    private readonly fn: (command: C) => Promise<R>,
  ) {}

  async execute(command: C): Promise<R> {
    return this.fn(command);
  }
}

export class QueryFunc<Q, R> implements QueryUseCase<Q, R> {
  constructor(
    private readonly fn: (query: Q) => Promise<R>,
  ) {}

  async execute(query: Q): Promise<R> {
    return this.fn(query);
  }
}

// DTO
export interface DTO<T> {
  data: T;
  meta?: DtoMeta;
}

export interface DtoMeta {
  version?: string;
  timestamp?: Date;
  requestId?: string;
}

export interface PaginatedResult<T> extends DTO<T[]> {
  paginated?: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

// Command
export interface Command {
  readonly type: string;
  readonly payload: Record<string, unknown>;
  readonly metadata?: Record<string, string>;
}

export class BaseCommand implements Command {
  constructor(
    public readonly type: string,
    public readonly payload: Record<string, unknown>,
    public readonly metadata: Record<string, string> = {},
  ) {}
}

// Query
export interface Query {
  readonly type: string;
  readonly filters?: QueryFilter[];
  readonly pagination?: PaginationInput;
}

export interface QueryFilter {
  field: string;
  operator: string;
  value: unknown;
}

export interface PaginationInput {
  page: number;
  pageSize: number;
}

// Application Error
export class ApplicationError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly cause?: Error,
  ) {
    super(message);
    this.name = 'ApplicationError';
  }
}

export const AppErrors = {
  Validation: (message: string) =>
    new ApplicationError('VALIDATION_ERROR', message),
  NotFound: (message: string) =>
    new ApplicationError('NOT_FOUND', message),
  Conflict: (message: string) =>
    new ApplicationError('CONFLICT', message),
};
