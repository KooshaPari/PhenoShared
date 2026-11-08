"""PhenoMCP tool implementations.

Exports all tool modules for discovery and registration.
"""

from pheno_mcp.tools.session_tools import (
    SESSION_TOOLS,
    TOOL_SESSION_SUSPEND,
    TOOL_SESSION_RESUME,
    handle_session_suspend,
    handle_session_resume,
    register_session_tools,
)
from pheno_mcp.tools.workflow_tools import (
    WORKFLOW_TOOLS,
    TOOL_WORKFLOW_EXECUTE,
    TOOL_WORKFLOW_STATUS,
    TOOL_WORKFLOW_CANCEL,
    TOOL_WORKFLOW_LIST,
    handle_workflow_execute,
    handle_workflow_status,
    handle_workflow_cancel,
    handle_workflow_list,
    register_workflow_tools,
)
from pheno_mcp.tools.governance_tools import (
    GOVERNANCE_TOOLS,
    TOOL_LEDGER_QUERY,
    TOOL_LEDGER_VERIFY,
    handle_ledger_query,
    handle_ledger_verify,
    register_governance_tools,
)
from pheno_mcp.tools.agent_tools import (
    AGENT_TOOLS,
    TOOL_AGENT_CREATE,
    TOOL_AGENT_LIST,
    TOOL_AGENT_GET,
    TOOL_AGENT_DELETE,
    handle_agent_create,
    handle_agent_list,
    handle_agent_get,
    handle_agent_delete,
    register_agent_tools,
)
from pheno_mcp.tools.knowledge_tools import (
    KNOWLEDGE_TOOLS,
    TOOL_KNOWLEDGE_STORE,
    TOOL_KNOWLEDGE_RETRIEVE,
    TOOL_KNOWLEDGE_SEARCH,
    TOOL_KNOWLEDGE_DELETE,
    handle_knowledge_store,
    handle_knowledge_retrieve,
    handle_knowledge_search,
    handle_knowledge_delete,
    register_knowledge_tools,
)
from pheno_mcp.tools.policy_tools import (
    POLICY_TOOLS,
    TOOL_POLICY_LIST,
    TOOL_POLICY_GET,
    TOOL_POLICY_EVALUATE,
    handle_policy_list,
    handle_policy_get,
    handle_policy_evaluate,
    register_policy_tools,
)

__all__ = [
    # Session tools
    "SESSION_TOOLS",
    "TOOL_SESSION_SUSPEND",
    "TOOL_SESSION_RESUME",
    "handle_session_suspend",
    "handle_session_resume",
    "register_session_tools",
    # Workflow tools
    "WORKFLOW_TOOLS",
    "TOOL_WORKFLOW_EXECUTE",
    "TOOL_WORKFLOW_STATUS",
    "TOOL_WORKFLOW_CANCEL",
    "TOOL_WORKFLOW_LIST",
    "handle_workflow_execute",
    "handle_workflow_status",
    "handle_workflow_cancel",
    "handle_workflow_list",
    "register_workflow_tools",
    # Governance tools
    "GOVERNANCE_TOOLS",
    "TOOL_LEDGER_QUERY",
    "TOOL_LEDGER_VERIFY",
    "handle_ledger_query",
    "handle_ledger_verify",
    "register_governance_tools",
    # Agent tools
    "AGENT_TOOLS",
    "TOOL_AGENT_CREATE",
    "TOOL_AGENT_LIST",
    "TOOL_AGENT_GET",
    "TOOL_AGENT_DELETE",
    "handle_agent_create",
    "handle_agent_list",
    "handle_agent_get",
    "handle_agent_delete",
    "register_agent_tools",
    # Knowledge tools
    "KNOWLEDGE_TOOLS",
    "TOOL_KNOWLEDGE_STORE",
    "TOOL_KNOWLEDGE_RETRIEVE",
    "TOOL_KNOWLEDGE_SEARCH",
    "TOOL_KNOWLEDGE_DELETE",
    "handle_knowledge_store",
    "handle_knowledge_retrieve",
    "handle_knowledge_search",
    "handle_knowledge_delete",
    "register_knowledge_tools",
    # Policy tools
    "POLICY_TOOLS",
    "TOOL_POLICY_LIST",
    "TOOL_POLICY_GET",
    "TOOL_POLICY_EVALUATE",
    "handle_policy_list",
    "handle_policy_get",
    "handle_policy_evaluate",
    "register_policy_tools",
]
