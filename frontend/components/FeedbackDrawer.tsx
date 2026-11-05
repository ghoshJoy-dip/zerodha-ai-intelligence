"use client";

import { useState } from "react";
import { submitFeedback } from "../lib/api";

const actions = [
  { value: "thumbs_up", label: "Helpful" },
  { value: "thumbs_down", label: "Not helpful" },
  { value: "accepted", label: "Accept" },
  { value: "dismissed", label: "Dismiss" },
] as const;

export default function FeedbackDrawer({ cardId }: { cardId: number }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(action: (typeof actions)[number]["value"]) {
    setBusy(true);
    setMessage("");
    try {
      await submitFeedback(cardId, action, note.trim() || undefined);
      setMessage("Feedback saved.");
      setNote("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save feedback.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="feedback-area">
      <button className="button button-quiet" onClick={() => setOpen((value) => !value)}>
        {open ? "Close feedback" : "Give feedback"}
      </button>
      {open && (
        <div className="feedback-drawer">
          <label htmlFor={`feedback-note-${cardId}`}>Optional note</label>
          <textarea
            id={`feedback-note-${cardId}`}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={2}
            maxLength={500}
            placeholder="What was useful or unclear?"
          />
          <div className="feedback-actions">
            {actions.map((action) => (
              <button
                key={action.value}
                className="button button-small"
                disabled={busy}
                onClick={() => void send(action.value)}
              >
                {action.label}
              </button>
            ))}
          </div>
          {message && <p className="feedback-message" role="status">{message}</p>}
        </div>
      )}
    </div>
  );
}
