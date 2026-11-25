/**
 * Copyright (c) 2023-present Plane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

"use client";

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/ui";
import { Badge } from "@plane/ui";
import { GitBranch, Plus, Activity } from "lucide-react";

export default observer(function WorktreesPage() {
  const { t } = useTranslation();
  const params = useParams();
  const workspaceSlug = params.workspaceSlug?.toString() ?? "";

  const [worktrees] = useState([
    { id: "wt-1", name: "feature-auth", branch: "feature/auth", status: "active", last_commit: "2h ago" },
    { id: "wt-2", name: "bugfix-sidebar", branch: "bugfix/sidebar", status: "inactive", last_commit: "1d ago" },
  ]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge color="green" size="sm">Active</Badge>;
      case "inactive":
        return <Badge color="gray" size="sm">Inactive</Badge>;
      case "syncing":
        return <Badge color="yellow" size="sm">Syncing</Badge>;
      default:
        return <Badge size="sm">{status}</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">
            {t("worktrees.title", "Worktrees")}
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            {t("worktrees.description", "Manage worktrees for this workspace.")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="neutral" size="sm">
            {t("worktrees.sync", "Sync All")}
          </Button>
          <Button size="sm" prependIcon={<Plus className="h-4 w-4" />}>
            {t("worktrees.create", "Create Worktree")}
          </Button>
        </div>
      </div>

      {worktrees.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {worktrees.map((wt) => (
            <div
              key={wt.id}
              className="p-4 border border-custom-border-200 rounded-lg hover:bg-custom-background-50 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-custom-background-80 text-custom-text-300 flex-shrink-0">
                  <GitBranch className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-text-primary truncate">
                      {wt.name}
                    </h3>
                    {getStatusBadge(wt.status)}
                  </div>
                  <p className="text-xs text-text-secondary truncate">
                    {wt.branch}
                  </p>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-xs text-text-secondary flex items-center gap-1">
                      <Activity className="h-3 w-3" />
                      {wt.last_commit}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 px-6 border border-dashed border-custom-border-200 rounded-lg">
          <div className="p-3 bg-custom-background-80 rounded-full mb-4">
            <GitBranch className="h-8 w-8 text-custom-text-400" />
          </div>
          <h3 className="text-lg font-medium text-text-primary mb-1">
            {t("worktrees.empty.title", "No worktrees yet")}
          </h3>
          <p className="text-sm text-text-secondary text-center mb-4 max-w-sm">
            {t("worktrees.empty.description", "Create your first worktree to get started.")}
          </p>
          <Button size="sm" prependIcon={<Plus className="h-4 w-4" />}>
            {t("worktrees.create", "Create Worktree")}
          </Button>
        </div>
      )}
    </div>
  );
});
