import { useEffect, useState } from "react";

import ChatPanel from "./components/ChatPanel";
import DocumentUpload from "./components/DocumentUpload";
import { API_BASE_URL } from "./config";

function App() {
  const [backendStatus, setBackendStatus] = useState("Checking...");

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

        setBackendStatus(data.status);
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

  function handleUploadSuccess(uploadResult) {
    setActiveDocument(uploadResult);
  }

  return (
    <main>
      <header>
        <h1>AI Document Search</h1>

        <p>Upload a PDF and ask questions using semantic search.</p>

        <p>
          Backend status: <strong>{backendStatus}</strong>
        </p>

        {backendError && <p role="alert">{backendError}</p>}
      </header>

      <DocumentUpload onUploadSuccess={handleUploadSuccess} />

      <ChatPanel
        key={activeDocument?.document_id ?? "no-document"}
        document={activeDocument}
      />
    </main>
  );
}

export default App;
