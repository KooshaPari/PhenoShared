/**
 * Normalised view models for the project and instance screens.
 *
 * This module is private to the project/instance views (the three route pages
 * and the project dialogs). It lives beside those components rather than in
 * `$lib` so it does not add shared-layer surface: if it later needs to be the
 * org-wide reader for these endpoints, promote it centrally instead of
 * importing it from elsewhere.
 *
 * Two problems this module exists to solve:
 *
 * 1. The Go models disagree about JSON spelling. `models.Project` carries
 *    snake_case tags (`access_url`, `last_updated`, `platform`, `type`) while
 *    `models.Instance` carries no tags at all, so it emits Go field names
 *    (`UUID`, `Name`, `Status`, `Resources`). The 2023 views hard-coded one
 *    spelling each (`project.Type`, `project.access_url`), which is why half
 *    the fields they rendered were silently `undefined`. `pick()` reads either
 *    spelling and the row types below are the single shape every view renders.
 *
 * 2. There was no vocabulary for state: no loading/empty/error distinction and
 *    no status classification, so each page invented its own. `statusTone()`
 *    and `formatRelative()` centralise that judgement.
 *
 * Endpoints are unchanged (`GET /projects`, `GET /instances`,
 * `POST /deploy`, `POST /terminate`); only the reading of the response is.
 */
import { apiFetch } from '../lib/api';
import { initializeUser, user } from '../stores/user';

/** Badge tones. Mirrors `src/lib/components/ui/Badge.svelte`. */
export type Tone = 'neutral' | 'primary' | 'info' | 'warning' | 'danger';

export interface ResourceRow {
	id: string;
	name: string;
	type: string;
	service: string;
	status: string;
	statusTone: Tone;
	arn: string;
	region: string;
}

export interface InstanceRow {
	uuid: string;
	name: string;
	status: string;
	statusTone: Tone;
	os: string;
	/** UUID of the project this instance was deployed from, when reported. */
	projectUuid: string;
	resources: ResourceRow[];
	lastUpdated: string | null;
	lastUpdatedLabel: string;
	raw: Record<string, unknown>;
}

export interface ProjectRow {
	uuid: string;
	name: string;
	description: string;
	type: string;
	platform: string;
	accessUrl: string;
	/** Host of `accessUrl`, or an empty string when there is no URL yet. */
	host: string;
	repoFullName: string;
	repoPrivate: boolean;
	repoUrl: string;
	lastDeployAt: string | null;
	lastDeployLabel: string;
	instances: InstanceRow[];
	total: number;
	running: number;
	failed: number;
	pending: number;
	/** Rolled-up deployment state, e.g. "2 running" or "Not deployed". */
	status: string;
	/** Machine-readable companion to `status`, for list filters. */
	statusKey: 'not-deployed' | 'deploying' | 'running' | 'failed' | 'stopped';
	statusTone: Tone;
	/** Human-readable deploy target, e.g. the repository full name. */
	target: string;
	raw: Record<string, unknown>;
}

/* ------------------------------------------------------------------ shape -- */

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * First present value among `keys`, trying exact keys before a loose
 * case-insensitive match that ignores `_` and `-`.
 *
 * This is what lets one reader accept `access_url`, `accessUrl` and `AccessURL`
 * from the same backend.
 */
export function pick(source: unknown, ...keys: string[]): unknown {
	if (!isRecord(source)) return undefined;

	for (const key of keys) {
		const value = source[key];
		if (value !== undefined && value !== null) return value;
	}

	const normalised = new Map<string, unknown>();
	for (const [key, value] of Object.entries(source)) {
		normalised.set(key.replace(/[_-]/g, '').toLowerCase(), value);
	}
	for (const key of keys) {
		const value = normalised.get(key.replace(/[_-]/g, '').toLowerCase());
		if (value !== undefined && value !== null) return value;
	}
	return undefined;
}

/** Coerce to a trimmed string; `undefined`/`null` become `''`. */
export function str(value: unknown): string {
	if (value === undefined || value === null) return '';
	if (typeof value === 'string') return value.trim();
	if (typeof value === 'number' || typeof value === 'boolean') return String(value);
	return '';
}

/** Coerce to an array of records, tolerating `null` and non-array payloads. */
export function rows(value: unknown): Record<string, unknown>[] {
	if (!Array.isArray(value)) return [];
	return value.filter(isRecord);
}

/* ----------------------------------------------------------------- state -- */

const FAILED = /fail|error|crash|unhealthy|unreachable|invalid|terminated/;
const RUNNING = /run|active|live|healthy|ready|deploy(ed)?$|success|complete|available|started/;
const PENDING = /build|deploy|provision|pend|start|creat|updat|sync|queu|progress|initial|request/;

/**
 * Classify a backend status string into a badge tone.
 *
 * Deliberately conservative: an unrecognised status is `neutral` rather than
 * guessed at. `warning` is not used here so the views stay on one accent plus
 * the destructive tinting that actually means something.
 */
export function statusTone(status: unknown): Tone {
	const value = str(status).toLowerCase();
	if (!value) return 'neutral';
	if (FAILED.test(value)) return 'danger';
	if (/\b(stop|halt|paused|idle|suspended|offline|down)\b/.test(value)) return 'neutral';
	if (RUNNING.test(value)) return 'primary';
	if (PENDING.test(value)) return 'info';
	return 'neutral';
}

/**
 * Compact relative time for table cells. Absolute values are exposed through
 * `formatAbsolute` for the `title` attribute, so precision is not lost.
 */
export function formatRelative(value: string | null | undefined, now = Date.now()): string {
	if (!value) return 'Never';
	const parsed = Date.parse(value);
	if (Number.isNaN(parsed)) return 'Unknown';

	const seconds = Math.round((now - parsed) / 1000);
	if (seconds < 45) return 'Just now';
	const minutes = Math.round(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.round(hours / 24);
	if (days < 30) return `${days}d ago`;
	return new Date(parsed).toLocaleDateString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

/** Full local timestamp for tooltips. Empty input yields `Never`. */
export function formatAbsolute(value: string | null | undefined): string {
	if (!value) return 'Never';
	const parsed = Date.parse(value);
	if (Number.isNaN(parsed)) return 'Unknown';
	return new Date(parsed).toLocaleString();
}

/** Host portion of a URL, or `''` when it is not parseable. */
export function hostOf(url: string): string {
	if (!url) return '';
	try {
		return new URL(url).host;
	} catch {
		return '';
	}
}

/* ------------------------------------------------------------- normalise -- */

function normalizeResource(raw: unknown): ResourceRow {
	const value = pick(raw, 'id', 'ID', 'resource_id') ?? pick(raw, 'arn');
	const status = str(pick(raw, 'status', 'Status', 'state'));
	return {
		id: str(value),
		name: str(pick(raw, 'name', 'Name')) || 'Unnamed resource',
		type: str(pick(raw, 'type', 'Type')) || 'resource',
		service: str(pick(raw, 'service', 'Service')) || 'unknown',
		status: status || 'unknown',
		statusTone: statusTone(status),
		arn: str(pick(raw, 'arn', 'ARN')),
		region: str(pick(raw, 'region', 'Region'))
	};
}

/**
 * Coerce a deployments payload into records.
 *
 * `models.Project` stores deployments in a `deployments` column and only exposes
 * them as `DeploymentsJSON`, a JSON *string*; the decoded map is a private field
 * with `json:"-"`. So the string form is the normal case, not an edge case.
 */
function coerceDeployments(value: unknown): Record<string, unknown>[] {
	if (!value) return [];

	if (typeof value === 'string') {
		const text = value.trim();
		if (!text) return [];
		try {
			return coerceDeployments(JSON.parse(text));
		} catch {
			// A malformed deployments blob must not blank the whole row.
			return [];
		}
	}
	if (Array.isArray(value)) return rows(value);
	if (isRecord(value)) return rows(Object.values(value));
	return [];
}

function parseDeployments(raw: unknown): Record<string, unknown>[] {
	return coerceDeployments(
		pick(raw, 'DeploymentsJSON', 'deployments_json', 'Deployments', 'deployments')
	);
}

/**
 * Resource list for an instance.
 *
 * Same trap as deployments, and worse: `models.Instance` has both a
 * `resources` JSON column (`ResourcesJSON`) and a `Resources []AWSResource`
 * relation, and `GetInstances` does not preload the relation. The relation is
 * therefore usually null and the JSON string is the only populated source, so
 * preferring the string is the correct default rather than a fallback.
 */
function parseResources(raw: unknown): ResourceRow[] {
	const inline = pick(raw, 'Resources', 'resources');
	const encoded = pick(raw, 'ResourcesJSON', 'resources_json');

	if (typeof encoded === 'string' && encoded.trim()) {
		try {
			const parsed = rows(JSON.parse(encoded.trim()));
			if (parsed.length > 0) return parsed.map(normalizeResource);
		} catch {
			// Fall through to the relation below.
		}
	}
	return rows(inline).map(normalizeResource);
}

export function normalizeInstance(raw: unknown, fallbackProject: string = ''): InstanceRow {
	const lastUpdated =
		str(pick(raw, 'last_updated', 'LastUpdated', 'UpdatedAt', 'updated_at', 'CreatedAt')) || null;
	const resources = parseResources(raw);
	const status = str(pick(raw, 'status', 'Status', 'state')) || 'unknown';

	return {
		uuid: str(pick(raw, 'UUID', 'uuid', 'id', 'ID')),
		name: str(pick(raw, 'Name', 'name')) || 'Unnamed instance',
		status,
		statusTone: statusTone(status),
		os: str(pick(raw, 'OS', 'os', 'platform', 'Platform')) || 'unknown',
		projectUuid:
			str(pick(raw, 'RootProjectUUID', 'root_project_uuid', 'ResUUID')) || fallbackProject,
		resources,
		lastUpdated,
		lastUpdatedLabel: formatRelative(lastUpdated),
		raw: isRecord(raw) ? raw : {}
	};
}

/**
 * Roll a project's instances up into one status line.
 *
 * A project has no status column of its own; "is it up" is entirely a function
 * of what it deployed, so the summary is derived rather than invented.
 */
function summarize(instances: InstanceRow[]): Pick<
	ProjectRow,
	'status' | 'statusTone' | 'statusKey'
> & {
	running: number;
	failed: number;
	pending: number;
} {
	const running = instances.filter((i) => i.statusTone === 'primary').length;
	const failed = instances.filter((i) => i.statusTone === 'danger').length;
	const pending = instances.filter((i) => i.statusTone === 'info').length;

	if (instances.length === 0) {
		return {
			status: 'Not deployed',
			statusKey: 'not-deployed',
			statusTone: 'neutral',
			running,
			failed,
			pending
		};
	}
	if (failed > 0) {
		return {
			status: failed === 1 ? '1 failed' : `${failed} failed`,
			statusKey: 'failed',
			statusTone: 'danger',
			running,
			failed,
			pending
		};
	}
	if (pending > 0) {
		return {
			status: 'Deploying',
			statusKey: 'deploying',
			statusTone: 'info',
			running,
			failed,
			pending
		};
	}
	if (running === instances.length) {
		return {
			status: running === 1 ? 'Running' : `${running} running`,
			statusKey: 'running',
			statusTone: 'primary',
			running,
			failed,
			pending
		};
	}
	return {
		status: running > 0 ? `${running} of ${instances.length} running` : 'Stopped',
		statusKey: 'stopped',
		statusTone: 'neutral',
		running,
		failed,
		pending
	};
}

export function normalizeProject(raw: unknown): ProjectRow {
	const repository = pick(raw, 'Repository', 'repository');
	const instances = parseDeployments(raw).map((item) => normalizeInstance(item));
	const accessUrl = str(pick(raw, 'access_url', 'accessUrl', 'AccessURL'));
	const lastDeployAt =
		str(pick(raw, 'last_updated', 'LastUpdated', 'UpdatedAt', 'updated_at', 'CreatedAt')) || null;
	const summary = summarize(instances);
	const repoFullName = str(pick(repository, 'full_name', 'FullName', 'name', 'Name'));

	return {
		uuid: str(pick(raw, 'UUID', 'uuid', 'id', 'ID')),
		name: str(pick(raw, 'name', 'Name')) || 'Untitled project',
		description: str(pick(raw, 'description', 'Description')),
		type: str(pick(raw, 'type', 'Type')) || 'unspecified',
		platform: str(pick(raw, 'platform', 'Platform')) || 'unspecified',
		accessUrl,
		host: hostOf(accessUrl),
		repoFullName,
		repoPrivate: Boolean(pick(repository, 'private', 'Private')),
		repoUrl: str(pick(repository, 'html_url', 'HTMLURL')),
		lastDeployAt,
		lastDeployLabel: formatRelative(lastDeployAt),
		instances,
		total: instances.length,
		target: repoFullName || 'Local workspace',
		...summary,
		raw: isRecord(raw) ? raw : {}
	};
}

/* ------------------------------------------------------------------ fetch -- */

/** `GET /projects`, normalised. Throws `ApiError` so callers can show status. */
export async function fetchProjects(): Promise<ProjectRow[]> {
	const payload = await apiFetch<unknown>('/projects');
	return rows(payload).map(normalizeProject);
}

/** `GET /instances`, normalised. */
export async function fetchInstances(): Promise<InstanceRow[]> {
	const payload = await apiFetch<unknown>('/instances');
	return rows(payload).map((item) => normalizeInstance(item));
}

/**
 * `POST /deploy`.
 *
 * Keys are lowercase to match the `json` tags on `models.Project`. Go's decoder
 * is case-insensitive, but sending the tagged spelling keeps this correct if
 * that ever changes.
 */
export async function deployProject(input: {
	name: string;
	description: string;
	type: string;
	platform: string;
	repository: unknown;
}): Promise<{ sandboxId: string; status: string }> {
	const payload = await apiFetch<Record<string, unknown>>('/deploy', {
		method: 'POST',
		body: JSON.stringify({
			name: input.name,
			description: input.description,
			type: input.type,
			platform: input.platform,
			repository: input.repository ?? null,
			readme: ''
		})
	});
	return { sandboxId: str(pick(payload, 'sandbox_id')), status: str(pick(payload, 'status')) };
}

/**
 * `POST /terminate`.
 *
 * The handler only reads `uuid` (it is passed to NanoVMS as the sandbox id), so
 * this sends an identity-only body instead of the whole project record, which
 * previously shipped the owner's AWS credentials back to the server.
 */
export async function terminateProject(uuid: string, name: string): Promise<void> {
	await apiFetch('/terminate', {
		method: 'POST',
		body: JSON.stringify({ uuid, name })
	});
}

/* ------------------------------------------------------------------- auth -- */

/**
 * Resolve the session once and keep the `/login` redirect working.
 *
 * The previous pages treated the store's initial `pending` state as
 * "unauthenticated", so landing directly on a deep link such as
 * `/home/instances` redirected to `/login` before the session had a chance to
 * resolve. `pending` now means "wait"; only an explicit `unauthenticated`
 * result navigates away.
 *
 * Returns a teardown that unsubscribes.
 */
export function watchAuth(
	navigate: (path: string) => void,
	onAuthenticated: (payload: unknown) => void
): () => void {
	void initializeUser();

	const unsubscribe = user.subscribe((value) => {
		if (value.status === 'pending') return;
		if (value.status !== 'authenticated') {
			navigate('/login');
			return;
		}
		onAuthenticated(value.data);
	});

	return unsubscribe;
}
