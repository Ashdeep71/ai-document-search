import { useState } from "react";

import { API_BASE_URL } from "../config";

function ChatPanel({ document }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    const cleanedQuestion = question.trim();

    if (!document) {
      setError("Upload a PDF before asking a question.");
      return;
    }

    if (!cleanedQuestion) {
      setError("Enter a question first.");
      return;
    }

    if (isSending) {
      return;
    }
    /*
    Take the existing conversation BEFORE adding
    the current question.

    Example:
    [
      {
        role: "user",
        content: "What are the recommendations?"
      },
      {
        role: "assistant",
        content: "The recommendations are..."
      }
    ]
  */
    const conversationHistory = messages.slice(-10).map((message) => ({
      role: message.role,
      content: message.content,
    }));

    setQuestion("");
    setError("");
    setIsSending(true);

    setMessages((previousMessages) => [
      ...previousMessages,
      {
        role: "user",
        content: cleanedQuestion,
      },
    ]);

    try {
      const response = await fetch(
        `${API_BASE_URL}/documents/${document.document_id}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: cleanedQuestion,
            k: 4,
            history: conversationHistory,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "The question could not be answered.");
      }

      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources ?? [],
        },
      ]);
    } catch (requestError) {
      if (requestError instanceof Error) {
        setError(requestError.message);
      } else {
        setError("Could not communicate with the backend.");
      }
    } finally {
      setIsSending(false);
    }
  }

  if (!document) {
    return (
      <section className="card chat-card">
        <h2>Document chat</h2>
        <p className="empty-state">Upload a PDF to begin asking questions.</p>
      </section>
    );
  }

  return (
    <section className="card chat-card">
      <div className="chat-header">
        <h2>Document chat</h2>
        <span className="chat-doc-name">{document.original_filename}</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="empty-state">
            Ask a question about the uploaded document.
          </p>
        )}

        {messages.map((message, messageIndex) => (
          <div
            key={`${message.role}-${messageIndex}`}
            className={`chat-message chat-message--${message.role}`}
          >
            <span className="sr-only">
              {message.role === "user" ? "You said:" : "Assistant said:"}
            </span>

            <div className="chat-bubble">{message.content}</div>

            {message.sources?.length > 0 && (
              <div className="chat-sources">
                {message.sources.map((source) => (
                  <span key={source.chunk_id} className="source-chip">
                    Source {source.source_number} &middot; {source.filename},
                    p.{source.page_number}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {isSending && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-bubble chat-bubble--pending">
              Searching the document...
            </div>
          </div>
        )}
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <label htmlFor="question" className="sr-only">
          Ask a question
        </label>

        <textarea
          id="question"
          className="chat-input"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What is the main idea of this document?"
          rows={2}
          disabled={isSending}
        />

        <button
          type="submit"
          className="btn btn-primary"
          disabled={isSending || !question.trim()}
        >
          {isSending ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && (
        <p className="banner banner--error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

export default ChatPanel;
