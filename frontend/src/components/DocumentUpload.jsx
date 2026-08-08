import { useState } from "react";

import { API_BASE_URL } from "../config";

function DocumentUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState("");

  function handleFileChange(event) {
    const file = event.target.files?.[0] ?? null;

    setSelectedFile(file);
    setUploadResult(null);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Please select a PDF first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setIsUploading(true);
    setUploadResult(null);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "The PDF upload failed.");
      }

      setUploadResult(data);

      // Send the successful upload result to App.jsx.
      onUploadSuccess?.(data);
    } catch (requestError) {
      if (requestError instanceof Error) {
        setError(requestError.message);
      } else {
        setError("Could not upload the PDF.");
      }
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section>
      <h2>Upload a document</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="pdf-file">Choose a PDF</label>

          <input
            id="pdf-file"
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
          />
        </div>

        {selectedFile && (
          <p>
            Selected file: <strong>{selectedFile.name}</strong>
          </p>
        )}

        <button type="submit" disabled={!selectedFile || isUploading}>
          {isUploading ? "Processing PDF..." : "Upload PDF"}
        </button>
      </form>

      {error && <p role="alert">Error: {error}</p>}

      {uploadResult && (
        <div>
          <h3>Document ready</h3>

          <p>Filename: {uploadResult.original_filename}</p>

          <p>Pages processed: {uploadResult.page_count}</p>

          <p>Chunks created: {uploadResult.chunk_count}</p>
        </div>
      )}
    </section>
  );
}

export default DocumentUpload;
