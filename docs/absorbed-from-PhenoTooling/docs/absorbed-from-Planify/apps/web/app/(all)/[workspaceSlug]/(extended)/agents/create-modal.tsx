/**
 * Copyright (c) 2023-present Plane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */

"use client";

import { useState } from "react";
import { Button, Badge, Spinner } from "@plane/ui";
import { Bot, Plus } from "lucide-react";

interface CreateAgentModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateAgentModal({ onClose, onSuccess }: CreateAgentModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("inactive");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/v1/workspaces/workspaceSlug/agents/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, status }),
      });
      
      if (response.ok) {
        onSuccess?.();
        onClose();
      }
    } catch (error) {
      console.error("Failed to create agent:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-custom-background-100 p-6 rounded-lg max-w-md w-full">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-lg bg-custom-background-80 flex items-center justify-center">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Create Agent</h2>
            <p className="text-sm text-text-secondary">Add a new AI agent</p>
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">Name</label>
            <input
              type="text"
              className="w-full px-3 py-2 rounded-lg border border-custom-border-200"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter agent name"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1.5">Description</label>
            <textarea
              className="w-full px-3 py-2 rounded-lg border border-custom-border-200"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the agent"
              rows={3}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1.5">Status</label>
            <select
              className="w-full px-3 py-2 rounded-lg border border-custom-border-200"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="inactive">Inactive</option>
              <option value="active">Active</option>
              <option value="training">Training</option>
            </select>
          </div>
          
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="neutral" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isSubmitting}>
              {isSubmitting ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
