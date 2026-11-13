# Comparison Matrix

## Feature Comparison

This document compares **Agent Wave** with similar tools in the AI agent orchestration space.

| Repository | Purpose | Key Features | Language/Framework | Maturity | Comparison |
|------------|---------|--------------|-------------------|----------|------------|
| **Agent Wave (this repo)** | Agent orchestration framework | Multi-agent wave execution, Agent lifecycle management, Parallel task dispatch | TypeScript/Bun | Planning | Planned orchestration layer |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Multi-agent workflows | DAG-based execution, State management, Human-in-loop | Python | Stable | Production-grade orchestration |
| [AutoGen](https://github.com/microsoft/autogen) | Multi-agent conversation | Agent collaboration, Role-based agents | Python | Stable | Microsoft-backed |
| [CrewAI](https://github.com/crewai/crewai) | Multi-agent orchestration | Role-based agents, Task delegation | Python | Stable | Popular for simple workflows |
| [AgentVerse](https://github.com/open-agi/agentverse) | Multi-agent simulation | Agent simulation, Task decomposition | Python | Beta | Research-focused |
| [Swarm](https://github.com/openai/swarm) | Multi-agent orchestration | Lightweight, Handoffs | Python | Experimental | OpenAI experimental |
| [Magentic](https://github.com/jxnl/magentic) | Multi-agent with LLMs | Type-safe, Streaming | Python | Stable | TypeScript/Python focus |
| [PydanticAI](https://github.com/pydantic/pydantic-ai) | Agentic AI | Type-safe, Model-agnostic | Python | Beta | Pydantic integration |
| [Microsoft Autogen](https://github.com/microsoft/autogen) | Multi-agent framework | Conversational agents, Code execution | Python | Stable | Enterprise-focused |

## Detailed Feature Comparison

### Orchestration Capabilities

| Feature | Agent Wave | LangGraph | AutoGen | CrewAI | Swarm |
|---------|-----------|-----------|---------|--------|-------|
| Wave-based Execution | ✅ (Planned) | ❌ | ❌ | ❌ | ❌ |
| Parallel Task Dispatch | ✅ (Planned) | ✅ | ✅ | ✅ | ✅ |
| DAG Workflow | ❌ | ✅ | ❌ | ❌ | ❌ |
| Agent Handoffs | ❌ | ❌ | ✅ | ✅ | ✅ |
| State Management | ❌ | ✅ | ✅ | ✅ | ❌ |
| Human-in-loop | ❌ | ✅ | ✅ | ✅ | ❌ |

### Lifecycle Management

| Feature | Agent Wave | LangGraph | AutoGen | CrewAI |
|---------|-----------|-----------|---------|--------|
| Health Endpoints | ✅ (Planned) | ❌ | ❌ | ❌ |
| Graceful Shutdown | ✅ (Planned) | ✅ | ✅ | ✅ |
| Structured Logging | ✅ (Planned) | ✅ | ✅ | ✅ |
| Observability | ❌ | ✅ | ✅ | ✅ |

### Current Status

| Aspect | Status |
|--------|--------|
| Repository Scaffolding | ✅ Complete |
| CI Configuration | ✅ Configured |
| Governance Docs | ✅ AGENTS.md, CLAUDE.md |
| Application Code | ❌ Not Started |
| Wave Execution | ❌ Not Started |
| Lifecycle Management | ❌ Not Started |

## Unique Value Proposition

Agent Wave aims to provide:

1. **Wave-Based Execution**: Coordinated parallel execution of agent tasks in "waves"
2. **Lifecycle Management**: Standardized startup, health, and shutdown for agents
3. **Phenotype Integration**: Part of the Phenotype ecosystem with MCP and AgentAPI++ integration
4. **Policy Federation**: Integration with agentops-policy-federation for governance

## Comparison to Similar Projects

### vs LangGraph

LangGraph is production-grade but:

- Complex DAG-based model may be overkill for simple workflows
- Python-only
- No wave-based concept
- No native lifecycle management

Agent Wave provides simpler wave-based model with lifecycle awareness.

### vs AutoGen

AutoGen is Microsoft-backed but:

- Conversational model doesn't fit batch orchestration
- No health/shutdown concepts
- Complex agent definitions

Agent Wave focuses on batch/orchestration use cases.

### vs CrewAI

CrewAI is popular but:

- Role-based, not wave-based
- No lifecycle management
- Python-only

Agent Wave provides wave-based coordination.

## Ecosystem Position

Agent Wave fits in the Phenotype ecosystem:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Agent Wave     │────▶│  AgentAPI++     │────▶│   CLI Agents    │
│ (Orchestration)  │     │  (Control)      │     │ (Claude, etc.)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        ▼                                               │
┌─────────────────┐                                     │
│ Policy Federation│◀────────────────────────────────────┘
│ (Governance)    │
└─────────────────┘
```

## References

- PRD: [PRD.md](PRD.md)
- Architecture: [docs/](docs/)
- Agent Wave: Part of [Phenotype ecosystem](https://github.com/phenotype)
