import React, { useState, useEffect } from 'react';
import { pusher } from '../utils/pusher';

export default function Chat({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    const channel = pusher.subscribe('chat');
    channel.bind('message', function(data) {
      setMessages((prev) => [...prev, data]);
    });
    return () => { pusher.unsubscribe('chat'); };
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();
    await fetch('/api/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: user.id, role: user.role, message: input })
    });
    setInput('');
  };

  return (
    <div>
      <div style={{height: 200, overflowY: 'scroll', border: '1px solid #ccc'}}>
        {messages.map((msg, i) => (
          <div key={i}><b>{msg.role}:</b> {msg.message}</div>
        ))}
      </div>
      <form onSubmit={sendMessage} style={{marginTop: 10}}>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="Type a message..." />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
