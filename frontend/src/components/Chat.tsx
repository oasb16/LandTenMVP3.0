/* eslint-disable @typescript-eslint/no-unused-vars */
"use client";
import React, { useState, useEffect, useRef } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { pusher } from "../utils/pusher";

const THREAD_ID = "default";

type ChatUser = {
  id: string;
  role: string;
};

type ChatAttachment = {
  url: string;
  content_type?: string;
  name?: string;
};

type ChatMessage = {
  client_id?: string;
  message?: string;
  role?: string;
  user_id?: string;
  type?: string;
  timestamp?: string;
  payload?: Record<string, unknown> | null;
  attachments?: ChatAttachment[];
  optimistic?: boolean;
};

const buildEndpoint = (path: string): string => {
  const base = (process.env.NEXT_PUBLIC_BACKEND_URL || "").replace(/\/$/, "");
  return `${base}${path}`;
};

export default function Chat({ user }: { user: ChatUser }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [uploading, setUploading] = useState<boolean>(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const handlerBoundRef = useRef<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (handlerBoundRef.current) return;
    if (!pusher) {
      setError("Real-time updates unavailable. Configure Pusher credentials.");
      setLoading(false);
      return;
    }
    const channelName = "chat";
    const eventName = "message";
    const channel = pusher.subscribe(channelName);
    const handler = (data: ChatMessage) => {
      setMessages((prev: ChatMessage[]) => {
        const existingIndex = data.client_id
          ? prev.findIndex((msg) => msg.client_id === data.client_id)
          : -1;
        if (existingIndex !== -1) {
          const updated = [...prev];
          updated[existingIndex] = {
            ...prev[existingIndex],
            ...data,
            optimistic: false,
          };
          return updated;
        }
        if (
          prev.some(
            (msg) =>
              msg.timestamp === data.timestamp &&
              msg.user_id === data.user_id &&
              msg.message === data.message
          )
        ) {
          return prev;
        }
        return [...prev, data];
      });
    };
    channel.bind(eventName, handler);
    handlerBoundRef.current = true;
    return () => {
      channel.unbind(eventName, handler);
      pusher?.unsubscribe(channelName);
      handlerBoundRef.current = false;
    };
  }, []);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(buildEndpoint(`/chat/history/${THREAD_ID}`));
        if (!res.ok) throw new Error(`History HTTP ${res.status}`);
        const data = await res.json();
        setMessages(data.messages || []);
      } catch (e) {
        setError("Failed to load history");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  const sendPayload = async (payload: ChatMessage, { optimistic = true }: { optimistic?: boolean } = {}) => {
    const endpoint = buildEndpoint("/chat/send");
    const timestamp = payload.timestamp || new Date().toISOString();
    const clientId = payload.client_id || `client-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const basePayload: ChatMessage & { thread_id: string } = {
      thread_id: THREAD_ID,
      type: payload.type || "text",
      client_id: clientId,
      attachments: payload.attachments,
      payload: payload.payload,
      message: payload.message,
      role: payload.role,
      user_id: payload.user_id,
      timestamp,
    };
    if (optimistic) {
      setMessages((prev: ChatMessage[]) => [...prev, { ...basePayload, optimistic: true }]);
    }
    try {
      await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(basePayload),
      });
    } catch (err) {
      setError("Failed to send message");
      if (optimistic) {
        setMessages((prev: ChatMessage[]) => prev.filter((msg) => msg.client_id !== clientId));
      }
      throw err;
    }
  };

  const handleSend = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    try {
      await sendPayload({
        message: text,
        role: user.role,
        user_id: user.id,
        type: "text",
      });
    } catch (_) {
      setInput(text);
    }
  };

  const handleSummarize = async () => {
    try {
      const res = await fetch(buildEndpoint(`/agent/summarize_thread/${THREAD_ID}`));
      if (!res.ok) throw new Error("summary failed");
      const data = await res.json();
      await sendPayload(
        {
          message: data.summary,
          role: "assistant",
          user_id: "agent",
          type: "summary",
        },
        { optimistic: false }
      );
    } catch (err) {
      setError("Failed to summarize thread");
    }
  };

  const handleInjectCard = async () => {
    try {
      await sendPayload(
        {
          message: "Preview card",
          role: "system",
          user_id: "system",
          type: "card",
          payload: {
            title: "Maintenance Visit",
            body: "Technician scheduled for tomorrow at 9am.",
          },
        },
        { optimistic: false }
      );
    } catch (err) {
      setError("Failed to inject card message");
    }
  };

  const handleFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!file) return;
    setUploading(true);
    try {
      const params = new URLSearchParams({
        filename: file.name,
        content_type: file.type || "application/octet-stream",
      });
      const metaRes = await fetch(buildEndpoint(`/media/upload_url?${params.toString()}`));
      if (!metaRes.ok) throw new Error("upload url failed");
      const { upload_url, asset_url } = await metaRes.json();
      await fetch(upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      await sendPayload({
        message: file.name,
        role: user.role,
        user_id: user.id,
        type: "attachment",
        attachments: [
          {
            url: asset_url,
            content_type: file.type || "application/octet-stream",
            name: file.name,
          },
        ],
      });
    } catch (err) {
      setError("Failed to upload attachment (configure MEDIA_BUCKET for full support)");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const renderContent = (msg: ChatMessage) => {
    if (msg.type === "attachment" && Array.isArray(msg.attachments)) {
      return msg.attachments.map((att: ChatAttachment, idx) => (
        <div key={idx}>
          <a href={att.url} target="_blank" rel="noreferrer" style={{ color: "#38bdf8" }}>
            {att.name || att.url}
          </a>
        </div>
      ));
    }
    if (msg.type === "summary") {
      return <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{msg.message}</pre>;
    }
    if (msg.type === "card" && msg.payload) {
      const card = msg.payload as { title?: string; body?: string };
      return (
        <div style={{ border: "1px solid #1f2937", borderRadius: 8, padding: 8 }}>
          <div style={{ fontWeight: 700 }}>{card.title ?? "Card"}</div>
          <div style={{ marginTop: 4 }}>{card.body ?? ""}</div>
        </div>
      );
    }
    return <div>{msg.message}</div>;
  };

  return (
    <div style={{ color: "#f8fafc" }}>
      {loading && <div>Loading chat...</div>}
      {error && (
        <div style={{ color: "#f97316", marginBottom: 8 }}>{error}</div>
      )}
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <button type="button" onClick={handleSummarize} style={{ padding: "6px 12px", borderRadius: 6 }}>
          Summarize Thread
        </button>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{ padding: "6px 12px", borderRadius: 6 }}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Attach File"}
        </button>
        <button type="button" onClick={handleInjectCard} style={{ padding: "6px 12px", borderRadius: 6 }}>
          Inject Card
        </button>
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: "none" }}
          onChange={handleFileSelected}
        />
      </div>
      <div
        ref={listRef}
        style={{
          height: 240,
          overflowY: "auto",
          border: "1px solid #1f2937",
          padding: 12,
          background: "#0f172a",
          color: "#e2e8f0",
          borderRadius: 8,
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={msg.client_id || msg.timestamp || i}
            style={{
              marginBottom: 12,
              opacity: msg.optimistic ? 0.6 : 1,
              background: msg.type === "summary" ? "#1e293b" : "transparent",
              padding: msg.type === "summary" ? 8 : 0,
              borderRadius: msg.type === "summary" ? 6 : 0,
            }}
          >
            <div style={{ fontWeight: 700 }}>{msg.role}</div>
            {renderContent(msg)}
          </div>
        ))}
      </div>
      <form onSubmit={handleSend} style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          style={{ flex: 1, padding: 8, borderRadius: 6, border: "1px solid #1f2937" }}
        />
        <button type="submit" style={{ padding: "8px 16px", borderRadius: 6 }}>
          Send
        </button>
      </form>
    </div>
  );
}
