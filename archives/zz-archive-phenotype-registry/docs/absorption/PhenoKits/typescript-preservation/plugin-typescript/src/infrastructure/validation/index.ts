// Wrap-Over: Zod validation adapter
import { z } from 'zod';

// Zod schema for Example
export const ExampleSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be less than 100 characters'),
  description: z.string().max(500).optional(),
});

export type ExampleInput = z.infer<typeof ExampleSchema>;

// Validation adapter using Zod (wrap over third-party validation library)
export class ZodValidator<T> {
  constructor(private schema: z.ZodSchema<T>) {}

  parse(data: unknown): T {
    return this.schema.parse(data);
  }

  safeParse(data: unknown): { success: true; data: T } | { success: false; error: Error } {
    const result = this.schema.safeParse(data);
    if (result.success) {
      return { success: true, data: result.data };
    }
    return { success: false, error: result.error };
  }
}

export const exampleValidator = new ZodValidator(ExampleSchema);
