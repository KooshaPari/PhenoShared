/**
 * @vitest-environment node
 */
import { describe, it, expect } from 'vitest';
import {
  UseCase,
  UseCaseFunc,
  CommandFunc,
  QueryFunc,
  DTO,
  PaginatedResult,
  Command,
  BaseCommand,
  Query,
  ApplicationError,
  AppErrors,
} from '../index';

describe('Application Layer', () => {
  describe('UseCase', () => {
    it('should define execute method', () => {
      const useCase: UseCase<string, number> = {
        execute: async (input: string) => input.length,
      };

      expect(useCase.execute).toBeDefined();
    });

    it('should transform input to output', async () => {
      const useCase: UseCase<string, number> = {
        execute: async (input: string) => input.length,
      };

      const result = await useCase.execute('hello world');
      expect(result).toBe(11);
    });
  });

  describe('UseCaseFunc', () => {
    it('should create use case from function', async () => {
      const useCase = new UseCaseFunc((input: string) => Promise.resolve(input.length));
      const result = await useCase.execute('hello');
      expect(result).toBe(5);
    });
  });

  describe('CommandFunc', () => {
    it('should create command use case from function', async () => {
      const cmd = new CommandFunc((command: { name: string }) =>
        Promise.resolve({ id: 'new-id', name: command.name })
      );

      const result = await cmd.execute({ name: 'Test' });
      expect(result.id).toBe('new-id');
    });
  });

  describe('QueryFunc', () => {
    it('should create query use case from function', async () => {
      const query = new QueryFunc((q: { id: string }) =>
        Promise.resolve({ id: q.id, name: 'Found' })
      );

      const result = await query.execute({ id: '123' });
      expect(result.name).toBe('Found');
    });
  });

  describe('DTO', () => {
    it('should create DTO with data', () => {
      const dto: DTO<{ name: string }> = {
        data: { name: 'Test' },
      };

      expect(dto.data.name).toBe('Test');
    });
  });

  describe('PaginatedResult', () => {
    it('should create paginated result', () => {
      const result: PaginatedResult<{ id: string }> = {
        data: [{ id: '1' }],
        paginated: {
          page: 1,
          pageSize: 10,
          total: 25,
          totalPages: 3,
        },
      };

      expect(result.data.length).toBe(1);
      expect(result.paginated?.totalPages).toBe(3);
    });
  });

  describe('Command', () => {
    it('should create command with type and payload', () => {
      const cmd: Command = {
        type: 'CreateUser',
        payload: { name: 'Test' },
      };

      expect(cmd.type).toBe('CreateUser');
      expect(cmd.payload.name).toBe('Test');
    });
  });

  describe('BaseCommand', () => {
    it('should create command with base implementation', () => {
      const cmd = new BaseCommand('DeleteUser', { id: '123' });
      expect(cmd.type).toBe('DeleteUser');
      expect(cmd.payload.id).toBe('123');
    });
  });

  describe('Query', () => {
    it('should create query with filters', () => {
      const query: Query = {
        type: 'GetUsers',
        pagination: { page: 1, pageSize: 10 },
      };

      expect(query.type).toBe('GetUsers');
      expect(query.pagination?.pageSize).toBe(10);
    });
  });

  describe('ApplicationError', () => {
    it('should create application error', () => {
      const error = new ApplicationError('VALIDATION_ERROR', 'Invalid input');
      expect(error.code).toBe('VALIDATION_ERROR');
      expect(error.name).toBe('ApplicationError');
    });
  });

  describe('AppErrors', () => {
    it('should create validation error', () => {
      const error = AppErrors.Validation('Field is required');
      expect(error.code).toBe('VALIDATION_ERROR');
    });

    it('should create not found error', () => {
      const error = AppErrors.NotFound('User not found');
      expect(error.code).toBe('NOT_FOUND');
    });

    it('should create conflict error', () => {
      const error = AppErrors.Conflict('Email already exists');
      expect(error.code).toBe('CONFLICT');
    });
  });
});
