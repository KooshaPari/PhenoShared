/**
 * Copyright (c) 2023-present Plane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

"use client";

import { useState } from "react";
import { Modal, Button, TextInput } from "@plane/ui";
import { Bot } from "lucide-react";

interface CreateAgentModalProps {
  workspaceSlug: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateAgentModal({ workspaceSlug, onClose, onSuccess }: CreateAgentModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("inactive");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceSlug}/agents/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, status }),
      });

      if (response.ok) {
        onSuccess?.();
        onClose();
      }
    } catch (err) {
      console.error("Failed to create agent:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen onClose={onClose} className="w-[500px]">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-custom-background-80">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Create Agent</h2>
            <p className="text-sm text-text-secondary">Add a new AI agent to this workspace</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Name</label>
            <TextInput
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter agent name"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Description</label>
            <textarea
              className="w-full px-3 py-2 rounded-lg border border-custom-border-200 bg-transparent"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this agent does"
              rows={3}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">Status</label>
            <select
              className="w-full px-3 py-2 rounded-lg border border-custom-border-200 bg-transparent"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="inactive">Inactive</option>
              <option value="active">Active</option>
              <option value="training">Training</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="neutral" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
