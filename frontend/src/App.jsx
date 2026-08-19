import { useEffect, useMemo, useState } from "react";

import ChatPanel from "./components/ChatPanel";
import DocumentUpload from "./components/DocumentUpload";
import { API_BASE_URL } from "./config";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");

  const [backendError, setBackendError] = useState("");

  const [activeDocument, setActiveDocument] = useState(null);

  useEffect(() => {
    async function checkBackend() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);

        if (!response.ok) {
          throw new Error("The backend returned an error.");
        }

        const data = await response.json();

        setBackendStatus(data.status === "ok" ? "online" : "offline");
      } catch (requestError) {
        setBackendStatus("offline");

        if (requestError instanceof Error) {
          setBackendError(requestError.message);
        } else {
          setBackendError("Could not connect to the backend.");
        }
      }
    }

    checkBackend();
  }, []);

  const statusLabel = useMemo(() => {
    if (backendStatus === "online") {
      return "Backend online";
    }

    if (backendStatus === "offline") {
      return "Backend offline";
    }

    return "Checking backend...";
  }, [backendStatus]);

  function handleUploadSuccess(uploadResult) {
    setActiveDocument(uploadResult);
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="app-title">
          <h1>AI Document Search</h1>

          <p className="app-subtitle">
            Upload a PDF and ask questions using semantic search.
          </p>
        </div>

        <span className={`status-pill status-pill--${backendStatus}`}>
          <span className="status-dot" />
          {statusLabel}
        </span>
      </header>

      {backendError && (
        <p className="banner banner--error" role="alert">
          {backendError}
        </p>
      )}

      <DocumentUpload onUploadSuccess={handleUploadSuccess} />

      <ChatPanel
        key={activeDocument?.document_id ?? "no-document"}
        document={activeDocument}
      />
    </main>
  );
}

export default App;
