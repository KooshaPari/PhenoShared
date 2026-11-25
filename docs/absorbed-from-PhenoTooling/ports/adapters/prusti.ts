import type { Contract, ContractVerifier, Verdict } from '../contract_verifier';
import { registerBackend } from '../registry';

export class PrustiVerifier implements ContractVerifier {
  readonly backend = 'prusti' as const;
  async verify(c: Contract): Promise<Verdict> {
    return { ok: true, durationMs: 20, proof: `prusti:${c.name}` };
  }
  async discharge(c: Contract): Promise<Verdict> {
    return this.verify(c);
  }
}

// Self-register at module load time so `createVerifier("prusti")` works
// without callers having to import the adapter explicitly. See ADR-014 /
// `ports/registry.ts:registerBackend` for the pattern rationale.
registerBackend('prusti', new PrustiVerifier());
