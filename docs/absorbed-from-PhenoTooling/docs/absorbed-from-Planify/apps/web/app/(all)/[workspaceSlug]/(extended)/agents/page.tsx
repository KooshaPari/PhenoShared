/**
 * Copyright (c) 2023-present Plane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

"use client";

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { useTranslation } from "@plane/i18n";
import { useAgents } from "@/core/hooks/use-agent";
import { Button } from "@plane/ui";
import { Badge } from "@plane/ui";
import { Spinner } from "@plane/ui";
import { Bot, Plus, MoreHorizontal, Activity } from "lucide-react";
import { CreateAgentModal } from "./create-agent-modal";

export default observer(function AgentsPage() {
  const { t } = useTranslation();
  const params = useParams();
  const workspaceSlug = params.workspaceSlug?.toString() ?? "";
  const { agents, isLoading, error, fetchAgents } = useAgents(workspaceSlug);
  const [showCreateModal, setShowCreateModal] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6">
        <p className="text-sm text-red-500 mb-2">Failed to load agents</p>
        <Button variant="neutral" size="sm" onClick={fetchAgents}>
          {t("common.retry", "Retry")}
        </Button>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge color="green" size="sm">Active</Badge>;
      case "inactive":
        return <Badge color="gray" size="sm">Inactive</Badge>;
      case "training":
        return <Badge color="yellow" size="sm">Training</Badge>;
      default:
        return <Badge size="sm">{status}</Badge>;
    }
  };

  return (
    <>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">
              {t("agents.title", "AI Agents")}
            </h1>
            <p className="text-sm text-text-secondary mt-1">
              {t("agents.description", "Manage your AI agents for this workspace.")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              prependIcon={<Plus className="h-4 w-4" />}
              onClick={() => setShowCreateModal(true)}
            >
              {t("agents.create", "Create Agent")}
            </Button>
          </div>
        </div>

        {/* Agents Grid */}
        {agents && agents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <div
                key={agent.id}
                className="p-4 border border-custom-border-200 rounded-lg hover:bg-custom-background-50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-custom-background-80 text-custom-text-300 flex-shrink-0">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div className="flex flex-col gap-y-0.5 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-medium text-text-primary truncate">
                          {agent.name}
                        </h3>
                        {getStatusBadge(agent.status)}
                      </div>
                      <p className="text-xs text-text-secondary truncate">
                        {agent.description || "No description"}
                      </p>
                      <div className="flex items-center gap-4 mt-1">
                        <span className="text-xs text-text-secondary flex items-center gap-1">
                          <Activity className="h-3 w-3" />
                          {agent.last_active || "Never"}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Button variant="neutral" size="sm" className="flex-shrink-0">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 px-6 border border-dashed border-custom-border-200 rounded-lg">
            <div className="p-3 bg-custom-background-80 rounded-full mb-4">
              <Bot className="h-8 w-8 text-custom-text-400" />
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-1">
              {t("agents.empty.title", "No agents yet")}
            </h3>
            <p className="text-sm text-text-secondary text-center mb-4 max-w-sm">
              {t("agents.empty.description", "Create your first AI agent to get started.")}
            </p>
            <Button
              size="sm"
              prependIcon={<Plus className="h-4 w-4" />}
              onClick={() => setShowCreateModal(true)}
            >
              {t("agents.create", "Create Agent")}
            </Button>
          </div>
        )}
      </div>

      {showCreateModal && (
        <CreateAgentModal
          workspaceSlug={workspaceSlug}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </>
  );
});
