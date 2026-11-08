/**
 * @phenotype/github-adapter - GitHub adapter for @phenotype/bot-framework
 * 
 * Absorbed from KooshaPari/AtomsBot (decomposed 2026-06-18)
 */
import type { Adapter, Message } from '@phenotype/sdk';

export interface GitHubConfig {
  token: string;
  owner?: string;
  repo?: string;
  webhookSecret?: string;
}

export interface GitHubEventInput {
  event: string;
  action: string;
  deliveryId: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

export type GitHubEventHandler = (event: GitHubEventInput) => Promise<void> | void;

/**
 * GitHubAdapter - Implements the Adapter contract from @phenotype/sdk for GitHub.
 * 
 * Wraps @octokit/rest for API access and exposes webhook event handlers.
 */
export class GitHubAdapter implements Adapter {
  readonly name = 'github';
  readonly version = '0.1.0';

  private config: GitHubConfig | null = null;
  private handlers: GitHubEventHandler[] = [];

  async init(config: GitHubConfig): Promise<void> {
    this.config = config;
    // In production:
    // const octokit = new Octokit({ auth: config.token });
    // this.octokit = octokit;
  }

  getState(): { ready: boolean; config: GitHubConfig | null } {
    return { ready: this.config !== null, config: this.config };
  }

  async shutdown(): Promise<void> {
    this.config = null;
    this.handlers = [];
  }

  onEvent(handler: GitHubEventHandler): void {
    this.handlers.push(handler);
  }

  /**
   * Translate a GitHub webhook event into the Phenotype Message format.
   */
  toPhenotypeMessage(input: GitHubEventInput): Message {
    const payload = input.payload;
    return {
      id: input.deliveryId,
      channel: `${payload.repository?.full_name ?? 'unknown'}`,
      author: payload.sender?.login ?? 'unknown',
      content: `${input.event}.${input.action}`,
      timestamp: input.timestamp,
      metadata: {
        event: input.event,
        action: input.action,
        payload,
        source: 'github',
      },
    };
  }
}

export default GitHubAdapter;
