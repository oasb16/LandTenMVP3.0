"use client";

import Chat from "@/components/Chat.js";

export default function LegacyChatPage() {
  const user = { id: "demo", role: "tenant" };
  return (
    <div style={{ padding: 16 }}>
      <h1>Legacy Pusher Chat</h1>
      <p style={{ color: '#94a3b8' }}>This route isolates the classic chat flow.</p>
      <Chat user={user} />
    </div>
  );
}

