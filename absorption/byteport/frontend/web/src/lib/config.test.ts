import { describe, expect, it } from 'vitest';
import { config } from './config';

describe('config windows paths', () => {
	it('keeps single backslashes (String.raw equivalence)', () => {
		expect(config.windows.tunnel.configPath).toBe('C:\\BytePort\\tunnels');
		expect(config.windows.tunnel.logPath).toBe('C:\\BytePort\\logs');
		expect(config.windows.storage.projectsPath).toBe('C:\\BytePort\\projects');
		expect(config.windows.storage.backupsPath).toBe('C:\\BytePort\\backups');
	});
});
