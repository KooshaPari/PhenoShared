# Contributing to Quillr

Thank you for your interest in contributing to Quillr!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/KooshaPari/quillr.git
cd quillr

# Install dependencies
npm install

# Run tests
npm test

# Build
npm run build
```

## Project Structure

```
src/
├── client.ts       # Core client implementation
├── interceptors/   # Request/response interceptors
├── retry/          # Retry logic with backoff
├── mock/           # Test mocking utilities
└── types.ts        # TypeScript type definitions
```

## Code Style

We use:
- **TypeScript**: Strict mode with full type coverage
- **ESLint**: For linting
- **Prettier**: For formatting

Run before committing:
```bash
npm run lint
npm run format
npm run check
```

## Testing

All contributions must include tests:

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
```

### Writing Tests

```typescript
import { describe, it, expect, vi } from 'vitest';
import { createClient } from '../src/client';

describe('Quillr Client', () => {
  it('should make type-safe requests', async () => {
    const client = createClient({ baseUrl: 'https://api.example.com' });
    const response = await client.get<User>('/users/1');
    expect(response).toBeDefined();
  });
});
```

## Pull Request Process

1. Create a feature branch from `main`
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

## Commit Messages

Format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`

Example: `feat(interceptors): add request transformation interceptor`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
