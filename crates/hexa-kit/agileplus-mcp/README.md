# AgilePlus MCP

> MCP server for AgilePlus work management integration

## Overview

AgilePlus MCP provides a Model Context Protocol (MCP) server that exposes AgilePlus work management capabilities to AI assistants and agents.

## Features

- **Work Item Access**: Query and manage work items
- **Sprint Management**: View and update sprint information
- **Team Coordination**: Access team assignments and capacity
- **Analytics**: Retrieve metrics and reports

## Quick Start

```bash
# Install
npm install -g @phenotype/agileplus-mcp

# Start server
agileplus-mcp serve --port 8080
```

## Configuration

```json
{
  "agileplus": {
    "apiUrl": "https://agileplus.example.com",
    "apiKey": "${AGILEPLUS_API_KEY}"
  }
}
```

## Documentation

- [Specification](SPEC.md) - Technical details
- [Implementation Plan](PLAN.md) - Development roadmap

## License

MIT
