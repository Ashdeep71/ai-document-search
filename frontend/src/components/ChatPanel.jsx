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
      <section>
        <h2>Document chat</h2>
        <p>Upload a PDF to begin asking questions.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Document chat</h2>

      <p>
        Active document: <strong>{document.original_filename}</strong>
      </p>

      <div>
        {messages.length === 0 && (
          <p>Ask a question about the uploaded document.</p>
        )}

        {messages.map((message, messageIndex) => (
          <article key={`${message.role}-${messageIndex}`}>
            <h3>{message.role === "user" ? "You" : "Assistant"}</h3>

            <p>{message.content}</p>

            {message.sources?.length > 0 && (
              <div>
                <h4>Sources</h4>

                <ul>
                  {message.sources.map((source) => (
                    <li key={source.chunk_id}>
                      Source {source.source_number}: {source.filename}, page{" "}
                      {source.page_number}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}

        {isSending && <p>Searching the document...</p>}
      </div>

      <form onSubmit={handleSubmit}>
        <label htmlFor="question">Ask a question</label>

        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What is the main idea of this document?"
          rows={4}
          disabled={isSending}
        />

        <button type="submit" disabled={isSending || !question.trim()}>
          {isSending ? "Generating answer..." : "Ask"}
        </button>
      </form>

      {error && <p role="alert">Error: {error}</p>}
    </section>
  );
}

export default ChatPanel;
