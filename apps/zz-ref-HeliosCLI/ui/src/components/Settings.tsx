import { useState } from "react";
import { useConfig } from "../hooks/useHelios";

export function Settings() {
  const { config, loading, addRepo, removeRepo } = useConfig();
  const [owner, setOwner] = useState("");
  const [repoName, setRepoName] = useState("");

  const handleAdd = async () => {
    if (!owner.trim() || !repoName.trim()) return;
    const ok = await addRepo(owner.trim(), repoName.trim());
    if (ok) {
      setOwner("");
      setRepoName("");
    }
  };

  const handleRemove = async (fullName: string) => {
    await removeRepo(fullName);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleAdd();
    }
  };

  return (
    <div className="settings-form">
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure monitored repositories and preferences</p>
      </div>

      <div className="settings-section">
        <h3>Add Repository</h3>
        <div className="form-group">
          <label>Owner / Organization</label>
          <input
            className="form-input"
            type="text"
            placeholder="e.g. kooshapari"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div className="form-group">
          <label>Repository Name</label>
          <div className="form-row">
            <input
              className="form-input"
              type="text"
              placeholder="e.g. helios-cli"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button className="btn btn-primary" onClick={handleAdd}>
              Add
            </button>
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h3>Monitored Repositories</h3>
        {loading && <p style={{ color: "var(--text-muted)" }}>Loading...</p>}

        {config && config.repos.length === 0 && (
          <p style={{ color: "var(--text-muted)", fontSize: 14 }}>
            No repositories configured. Add one above.
          </p>
        )}

        {config && config.repos.length > 0 && (
          <div className="repo-list-settings">
            {config.repos.map((repo) => {
              const fullName = `${repo.owner}/${repo.name}`;
              return (
                <div className="repo-list-item" key={fullName}>
                  <span className="name">{fullName}</span>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleRemove(fullName)}
                  >
                    Remove
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="settings-section">
        <h3>GitHub Token</h3>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            marginBottom: 12,
          }}
        >
          Token is resolved automatically from <code>GITHUB_TOKEN</code>{" "}
          environment variable or the <code>gh</code> CLI. No manual entry
          needed if either is configured.
        </p>
        <div className="form-group">
          <label>Refresh Interval (seconds)</label>
          <input
            className="form-input"
            type="number"
            min={10}
            max={300}
            defaultValue={config?.refresh_interval_secs ?? 60}
            style={{ width: 120 }}
          />
        </div>
      </div>
    </div>
  );
}
