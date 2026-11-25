/**
 * @phenotype/discord-adapter - Discord adapter for @phenotype/bot-framework
 * 
 * Absorbed from KooshaPari/AtomsBot (decomposed 2026-06-18)
 */
import type { Adapter, Message } from '@phenotype/sdk';

export interface DiscordConfig {
  token: string;
  intents?: number[];
  clientId?: string;
  guildId?: string;
}

export interface DiscordMessageInput {
  id: string;
  channelId: string;
  authorId: string;
  authorName: string;
  content: string;
  timestamp: number;
  raw?: unknown;
}

export type DiscordMessageHandler = (msg: DiscordMessageInput) => Promise<void> | void;

/**
 * DiscordAdapter - Implements the Adapter contract from @phenotype/sdk for Discord.
 * 
 * Wraps discord.js Client to translate Discord events to Phenotype Message format.
 * 
 * Note: This is a structural skeleton. To use with a real Discord bot, install
 * `discord.js` and implement the `init()` body to wire up the Client events.
 */
export class DiscordAdapter implements Adapter {
  readonly name = 'discord';
  readonly version = '0.1.0';

  private config: DiscordConfig | null = null;
  private handlers: DiscordMessageHandler[] = [];

  async init(config: DiscordConfig): Promise<void> {
    this.config = config;
    // In production:
    // const client = new Client({ intents: [GatewayIntentBits.Guilds, ...] });
    // client.on(Events.MessageCreate, msg => this.handle(msg));
    // await client.login(config.token);
  }

  getState(): { ready: boolean; config: DiscordConfig | null } {
    return { ready: this.config !== null, config: this.config };
  }

  async shutdown(): Promise<void> {
    this.config = null;
    this.handlers = [];
  }

  onMessage(handler: DiscordMessageHandler): void {
    this.handlers.push(handler);
  }

  /**
   * Translate a discord.js Message into the Phenotype Message format.
   * Useful for tests and for downstream code that consumes Phenotype Messages.
   */
  toPhenotypeMessage(input: DiscordMessageInput): Message {
    return {
      id: input.id,
      channel: input.channelId,
      author: input.authorId,
      content: input.content,
      timestamp: input.timestamp,
      metadata: {
        authorName: input.authorName,
        raw: input.raw,
        source: 'discord',
      },
    };
  }
}

export default DiscordAdapter;
