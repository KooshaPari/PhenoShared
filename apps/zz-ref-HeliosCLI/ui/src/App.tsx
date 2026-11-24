import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./components/Dashboard";
import { CIStatusPanel } from "./components/CIStatus";
import { IssueList } from "./components/IssueList";
import { PRList } from "./components/PRList";
import { Settings } from "./components/Settings";
import type { Page } from "./types";

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);

  const handleSelectRepo = (fullName: string) => {
    setSelectedRepo(fullName);
    setPage("ci");
  };

  const renderPage = () => {
    switch (page) {
      case "dashboard":
        return <Dashboard onSelectRepo={handleSelectRepo} />;
      case "ci":
        return (
          <CIStatusPanel
            fullName={selectedRepo}
            onBack={() => setPage("dashboard")}
          />
        );
      case "issues":
        return (
          <IssueList
            fullName={selectedRepo}
            onBack={() => setPage("dashboard")}
          />
        );
      case "prs":
        return (
          <PRList
            fullName={selectedRepo}
            onBack={() => setPage("dashboard")}
          />
        );
      case "settings":
        return <Settings />;
      default:
        return <Dashboard onSelectRepo={handleSelectRepo} />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        currentPage={page}
        onNavigate={setPage}
        selectedRepo={selectedRepo}
      />
      <main className="main-content">{renderPage()}</main>
    </div>
  );
}

export default App;
