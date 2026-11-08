/**
 * Copyright (c) 2023-present Plane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

"use client";

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams, useNavigate } from "react-router";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/ui";
import { Badge } from "@plane/ui";
import { Bot, Trash2, ArrowLeft } from "lucide-react";

const AgentDetailPage = observer(function AgentDetailPage() {
  const { t } = useTranslation();
  const params = useParams();
  const navigate = useNavigate();
  const workspaceSlug = params.workspaceSlug?.toString() ?? "";
  const agentId = params.agentId?.toString() ?? "";

  const [activeTab, setActiveTab] = useState<"overview" | "config" | "activity">("overview");

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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-custom-border-200">
        <div className="flex items-center gap-4">
          <Button variant="neutral" size="sm" onClick={() => navigate(`/${workspaceSlug}/agents`)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-custom-background-80">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">Agent: {agentId}</h1>
              <p className="text-sm text-text-secondary">Agent detail view</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {/* Tabs */}
        <div className="border-b border-custom-border-200 mb-6">
          <div className="flex gap-4">
            <button
              className={`pb-2 px-1 text-sm font-medium border-b-2 ${
                activeTab === "overview" ? "border-custom-border-100 text-text-primary" : "border-transparent text-text-secondary"
              }`}
              onClick={() => setActiveTab("overview")}
            >
              Overview
            </button>
            <button
              className={`pb-2 px-1 text-sm font-medium border-b-2 ${
                activeTab === "config" ? "border-custom-border-100 text-text-primary" : "border-transparent text-text-secondary"
              }`}
              onClick={() => setActiveTab("config")}
            >
              Configuration
            </button>
            <button
              className={`pb-2 px-1 text-sm font-medium border-b-2 ${
                activeTab === "activity" ? "border-custom-border-100 text-text-primary" : "border-transparent text-text-secondary"
              }`}
              onClick={() => setActiveTab("activity")}
            >
              Activity
            </button>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Agent Configuration</h3>
            <p className="text-sm text-text-secondary">
              Configure agent settings and behavior here.
            </p>
          </div>
        )}

        {activeTab === "config" && (
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Agent Configuration</h3>
            <textarea
              className="w-full h-64 px-3 py-2 rounded-lg border border-custom-border-200 font-mono text-sm"
              defaultValue={`{
  "name": "agent-${agentId}",
  "status": "inactive"
}`}
              placeholder='{"key": "value"}'
            />
            <div className="flex justify-end">
              <Button size="sm">Save Changes</Button>
            </div>
          </div>
        )}

        {activeTab === "activity" && (
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Recent Activity</h3>
            <p className="text-sm text-text-secondary">No activity recorded</p>
          </div>
        )}
      </div>
    </div>
  );
});

export default AgentDetailPage;
