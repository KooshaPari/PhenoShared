# AgilePlus MCP Specification

> MCP server for AgilePlus integration

## Overview

AgilePlus MCP implements the Model Context Protocol to expose work management data and operations.

## Resources

### Work Items
- `agileplus://work-items/{id}` - Individual work item
- `agileplus://work-items?status={status}` - Filtered list

### Sprints
- `agileplus://sprints/{id}` - Sprint details
- `agileplus://sprints/current` - Current active sprint

### Teams
- `agileplus://teams/{id}` - Team information
- `agileplus://teams/{id}/capacity` - Team capacity

## Tools

### Query Tools
- `get_work_item` - Retrieve work item by ID
- `list_work_items` - List work items with filters
- `get_sprint` - Get sprint information
- `get_team_capacity` - Check team capacity

### Action Tools
- `create_work_item` - Create new work item
- `update_work_item` - Update existing work item
- `assign_work_item` - Assign to team member
- `move_to_sprint` - Move item to different sprint

## API

```typescript
interface AgilePlusMCPConfig {
  apiUrl: string;
  apiKey: string;
  organization: string;
  defaultTeam?: string;
}
```

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
