/**
 * @phenotype/bot-framework - Bot orchestration framework
 * 
 * Absorbed from KooshaPari/AtomsBot (decomposed 2026-06-18)
 * Provides reusable bot lifecycle management, adapter registration, and message routing.
 */
import type { Adapter, Bot, Message } from '@phenotype/sdk';

export interface BotConfig {
  id: string;
  name: string;
  adapters?: Adapter[];
  logger?: Logger;
}

export interface Logger {
  info(msg: string, meta?: Record<string, unknown>): void;
  warn(msg: string, meta?: Record<string, unknown>): void;
  error(msg: string, meta?: Record<string, unknown>): void;
  debug(msg: string, meta?: Record<string, unknown>): void;
}

export interface MessageHandler {
  (message: Message): Promise<void> | void;
}

export interface Router {
  route(message: Message): Promise<MessageHandler | null>;
  register(pattern: RegExp | string, handler: MessageHandler): void;
}

export class SimpleRouter implements Router {
  private routes: Array<{ pattern: RegExp | string; handler: MessageHandler }> = [];

  register(pattern: RegExp | string, handler: MessageHandler): void {
    this.routes.push({ pattern, handler });
  }

  async route(message: Message): Promise<MessageHandler | null> {
    for (const { pattern, handler } of this.routes) {
      const matches = typeof pattern === 'string'
        ? message.content.includes(pattern)
        : pattern.test(message.content);
      if (matches) return handler;
    }
    return null;
  }
}

export class PhenotypeBot implements Bot {
  readonly id: string;
  readonly name: string;
  private adapters = new Map<string, Adapter>();
  private router: Router;
  private logger: Logger;
  private running = false;

  constructor(config: BotConfig) {
    this.id = config.id;
    this.name = config.name;
    this.router = new SimpleRouter();
    this.logger = config.logger ?? consoleLogger(`${config.name}`);
    config.adapters?.forEach(a => this.registerAdapter(a));
  }

  registerAdapter(adapter: Adapter): void {
    this.adapters.set(adapter.name, adapter);
    this.logger.info(`Adapter registered: ${adapter.name} v${adapter.version}`);
  }

  registerHandler(pattern: RegExp | string, handler: MessageHandler): void {
    this.router.register(pattern, handler);
  }

  async start(): Promise<void> {
    this.running = true;
    for (const adapter of this.adapters.values()) {
      await adapter.init({});
    }
    this.logger.info(`Bot ${this.name} started with ${this.adapters.size} adapters`);
  }

  async stop(): Promise<void> {
    this.running = false;
    for (const adapter of this.adapters.values()) {
      await adapter.shutdown();
    }
    this.logger.info(`Bot ${this.name} stopped`);
  }

  async handleMessage(message: Message): Promise<void> {
    const handler = await this.router.route(message);
    if (handler) {
      await handler(message);
    } else {
      this.logger.debug(`No handler for message: ${message.id}`);
    }
  }
}

function consoleLogger(name: string): Logger {
  return {
    info: (msg, meta) => console.log(`[${name}] INFO: ${msg}`, meta ?? ''),
    warn: (msg, meta) => console.warn(`[${name}] WARN: ${msg}`, meta ?? ''),
    error: (msg, meta) => console.error(`[${name}] ERROR: ${msg}`, meta ?? ''),
    debug: (msg, meta) => console.debug(`[${name}] DEBUG: ${msg}`, meta ?? ''),
  };
}

export { PhenotypeBot as Bot };
