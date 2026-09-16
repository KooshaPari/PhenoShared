// Configuration for BytePort Windows deployment
export const config = {
	// API Configuration
	api: {
		// Use environment variable or default to Windows setup port
		baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8081',
		nvmsUrl: import.meta.env.VITE_NVMS_URL || 'http://localhost:3000',
		timeout: 30000 // 30 seconds
	},

	// Deployment Configuration
	deployment: {
		// Windows-specific deployment settings
		platform: 'windows',
		containerRuntime: 'docker',
		tunnelProvider: 'cloudflare',

		// Default ports for services
		defaultPorts: {
			main: 8080,
			api: 8081,
			database: 5432,
			redis: 6379
		},

		// Supported project types
		supportedTypes: ['nodejs', 'go', 'python', 'rust', 'static']
	},

	// UI Configuration
	ui: {
		// Polling intervals
		statusPollInterval: 5000, // 5 seconds
		logPollInterval: 2000, // 2 seconds

		// Deployment status messages
		statusMessages: {
			initializing: 'Initializing deployment...',
			building: 'Building Docker container...',
			deploying: 'Starting container...',
			networking: 'Setting up tunnel...',
			completed: 'Deployment completed successfully!',
			failed: 'Deployment failed',
			terminating: 'Terminating project...',
			terminated: 'Project terminated successfully'
		},

		// Windows-specific status indicators
		windowsStatuses: {
			'container-building': 'Building Docker image',
			'container-starting': 'Starting container',
			'tunnel-creating': 'Creating Cloudflare tunnel',
			'tunnel-starting': 'Starting tunnel',
			ready: 'Project is live'
		}
	},

	// Feature flags for Windows deployment
	features: {
		// Enable Windows-specific features
		dockerDeployment: true,
		cloudflareTunnels: true,
		localStorage: true,

		// Disable AWS-specific features
		awsDeployment: false,
		s3Storage: false,
		ec2Instances: false,
		albLoadBalancer: false,

		// Development features
		devMode: import.meta.env.DEV,
		debugLogs: import.meta.env.DEV
	},

	// Windows deployment specific settings
	windows: {
		// Docker settings
		docker: {
			network: 'byteport-network',
			imagePrefix: 'byteport-',
			containerPrefix: 'byteport-'
		},

		// Tunnel settings
		tunnel: {
			configPath: 'C:\\BytePort\\tunnels',
			logPath: 'C:\\BytePort\\logs',
			defaultDomain: 'yourdomain.com'
		},

		// Storage settings
		storage: {
			projectsPath: 'C:\\BytePort\\projects',
			backupsPath: 'C:\\BytePort\\backups'
		}
	}
};

// Helper functions for API calls
export const apiHelpers = {
	// Get full API URL
	getApiUrl: (endpoint: string) => {
		return `${config.api.baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
	},

	// Get full NVMS URL
	getNvmsUrl: (endpoint: string) => {
		return `${config.api.nvmsUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
	},

	// Default fetch options
	getDefaultOptions: () => ({
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include' as RequestCredentials
	}),

	// Make API request with error handling
	makeRequest: async (url: string, options: RequestInit = {}) => {
		const defaultOptions = apiHelpers.getDefaultOptions();
		const mergedOptions = {
			...defaultOptions,
			...options,
			headers: {
				...defaultOptions.headers,
				...options.headers
			}
		};

		try {
			const response = await fetch(url, mergedOptions);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
				throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
			}

			return response;
		} catch (error) {
			console.error('API request failed:', error);
			throw error;
		}
	}
};

// Export default config
export default config;
