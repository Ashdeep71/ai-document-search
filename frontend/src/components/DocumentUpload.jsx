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
    <section className="card">
      <div>
        <h2>Upload a document</h2>
        <p className="card-hint">PDF files up to 10 MB.</p>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <div className="file-field">
          <input
            id="pdf-file"
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="file-input-hidden"
          />

          <label htmlFor="pdf-file" className="file-trigger">
            Choose a PDF
          </label>

          <p className="file-chip">
            {selectedFile ? `Selected: ${selectedFile.name}` : "No file chosen"}
          </p>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={!selectedFile || isUploading}
        >
          {isUploading ? "Processing PDF..." : "Upload PDF"}
        </button>
      </form>

      {error && (
        <p className="banner banner--error" role="alert">
          {error}
        </p>
      )}

      {uploadResult && (
        <div className="result-card">
          <h3>Document ready</h3>

          <dl className="result-stats">
            <div>
              <dt>Filename</dt>
              <dd>{uploadResult.original_filename}</dd>
            </div>

            <div>
              <dt>Pages</dt>
              <dd>{uploadResult.page_count}</dd>
            </div>

            <div>
              <dt>Chunks</dt>
              <dd>{uploadResult.chunk_count}</dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  );
}

export default DocumentUpload;
