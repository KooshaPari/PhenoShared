/// <reference path="./.sst/platform/config.d.ts" />

export default $config({
  app(input) {
    return {
      name: "4sgm-chatbot",
      removal: input?.stage === "production" ? "retain" : "remove",
      home: "aws",
      providers: {
        aws: {
          region: "us-east-1", // Change to your preferred region
        },
      },
    };
  },
  async run() {
    // Secrets (set via: sst secret set <name> <value>)
    const supabaseUrl = new sst.Secret("SupabaseUrl");
    const supabaseKey = new sst.Secret("SupabaseKey");
    const anthropicKey = new sst.Secret("AnthropicApiKey");
    const openaiKey = new sst.Secret("OpenAIApiKey");

    // VPC for secure AWS resources (optional but recommended for production)
    const vpc = new sst.aws.Vpc("ChatbotVpc", {
      nat: "managed", // Managed NAT gateway for Lambda internet access
    });

    // Backend API (FastAPI on Lambda with Function URL)
    const api = new sst.aws.Function("ChatAPI", {
      handler: "backend/lambda_handler.handler",
      runtime: "python3.12",
      timeout: "30 seconds",
      memory: "2 GB", // Increased for embedding generation
      architecture: "arm64", // Graviton2 for better price/performance
      link: [supabaseUrl, supabaseKey, anthropicKey, openaiKey],
      url: {
        cors: {
          allowOrigins: ["*"], // Restrict in production
          allowMethods: ["GET", "POST", "OPTIONS"],
          allowHeaders: ["Content-Type", "Authorization"],
        },
      },
      environment: {
        STAGE: $app.stage,
        POWERTOOLS_SERVICE_NAME: "4sgm-chatbot",
        LOG_LEVEL: $app.stage === "production" ? "INFO" : "DEBUG",
      },
      logging: {
        retention: "1 week",
      },
      // Optional: Deploy in VPC for enhanced security
      // vpc: {
      //   securityGroups: [vpc.securityGroups[0]],
      //   subnets: vpc.privateSubnets,
      // },
    });

    // API Gateway (alternative to Function URL for more control)
    const apiGateway = new sst.aws.ApiGatewayV2("ChatbotApi", {
      cors: {
        allowOrigins: ["*"], // Restrict in production
        allowMethods: ["GET", "POST", "OPTIONS"],
        allowHeaders: ["Content-Type", "Authorization"],
      },
    });

    apiGateway.route("POST /chat", {
      handler: "backend/lambda_handler.handler",
      runtime: "python3.12",
      timeout: "30 seconds",
      memory: "2 GB",
      architecture: "arm64",
      link: [supabaseUrl, supabaseKey, anthropicKey, openaiKey],
      environment: {
        STAGE: $app.stage,
      },
    });

    apiGateway.route("GET /health", {
      handler: "backend/lambda_handler.health_handler",
      runtime: "python3.12",
      timeout: "10 seconds",
      memory: "512 MB",
    });

    apiGateway.route("GET /mcp/health", {
      handler: "backend/lambda_handler.mcp_health_handler",
      runtime: "python3.12",
      timeout: "10 seconds",
      memory: "512 MB",
    });

    // S3 Bucket for static assets and document storage
    const docsBucket = new sst.aws.Bucket("DocumentsBucket", {
      public: false,
    });

    // CloudFront CDN for Frontend
    const cdn = new sst.aws.Cdn("ChatbotCDN", {
      comment: "4SGM Chatbot CDN",
      origins: [
        {
          domainName: "placeholder.example.com", // Will be replaced by Next.js deployment
        },
      ],
      defaultCacheBehavior: {
        allowedMethods: ["GET", "HEAD", "OPTIONS"],
        cachedMethods: ["GET", "HEAD"],
        compress: true,
        viewerProtocolPolicy: "redirect-to-https",
      },
    });

    // Frontend (Next.js on AWS)
    const web = new sst.aws.Nextjs("ChatbotWidget", {
      path: "frontend/",
      environment: {
        NEXT_PUBLIC_API_URL: apiGateway.url,
        NEXT_PUBLIC_STAGE: $app.stage,
      },
      domain: {
        // Uncomment and configure for custom domain
        // name: $app.stage === "production"
        //   ? "chatbot.4sgm.com"
        //   : `chatbot-${$app.stage}.4sgm.com`,
        // dns: sst.aws.dns(),
      },
      // Deploy to Lambda@Edge for global performance
      edge: false, // Set to true for edge deployment
      warm: $app.stage === "production" ? 10 : 0, // Keep 10 instances warm in prod
    });

    // DynamoDB for session state (alternative to Supabase for AWS-native)
    const sessionsTable = new sst.aws.Dynamo("ChatSessions", {
      fields: {
        sessionId: "string",
        userId: "string",
        timestamp: "number",
      },
      primaryIndex: { hashKey: "sessionId", rangeKey: "timestamp" },
      globalIndexes: {
        UserIndex: { hashKey: "userId", rangeKey: "timestamp" },
      },
      ttl: "expiresAt", // Auto-delete old sessions
    });

    // CloudWatch Log Group for structured logging
    const logGroup = new sst.aws.CloudWatchLogGroup("ChatbotLogs", {
      retentionInDays: $app.stage === "production" ? 30 : 7,
    });

    // CloudWatch Alarms for monitoring
    const errorAlarm = new sst.aws.CloudWatchAlarm("ChatbotErrors", {
      metric: {
        namespace: "AWS/Lambda",
        metricName: "Errors",
        dimensions: {
          FunctionName: api.name,
        },
        statistic: "Sum",
        period: 300, // 5 minutes
      },
      threshold: 10,
      comparisonOperator: "GreaterThanThreshold",
      evaluationPeriods: 1,
      // Configure SNS topic for alerts
      // alarmActions: [snsTopicArn],
    });

    // SNS Topic for escalations (notify support team)
    const escalationTopic = new sst.aws.SnsTopic("EscalationNotifications");
    escalationTopic.subscribe("support@4sgm.com", "email");

    // EventBridge for scheduled embedding updates
    const embeddingSync = new sst.aws.Cron("EmbeddingSync", {
      schedule: "rate(1 hour)", // Sync every hour
      job: {
        handler: "backend/jobs/sync_embeddings.handler",
        runtime: "python3.12",
        timeout: "5 minutes",
        memory: "2 GB",
        link: [supabaseUrl, supabaseKey, openaiKey],
      },
    });

    // SQS Queue for async escalation processing
    const escalationQueue = new sst.aws.Queue("EscalationQueue", {
      fifo: true,
    });

    escalationQueue.subscribe({
      handler: "backend/jobs/process_escalation.handler",
      runtime: "python3.12",
      timeout: "30 seconds",
      link: [escalationTopic],
    });

    // Outputs
    return {
      api: api.url,
      apiGateway: apiGateway.url,
      web: web.url,
      docsBucket: docsBucket.name,
      sessionsTable: sessionsTable.name,
      region: $app.providers.aws.region,
    };
  },
});
