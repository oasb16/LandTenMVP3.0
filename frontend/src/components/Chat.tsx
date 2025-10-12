import React, { useState } from 'react';

export default function Chat() {
  const [messages, setMessages] = useState<string[]>([]);
  const [input, setInput] = useState('');

  const sendMessage = () => {
    if (input.trim()) {
      setMessages([...messages, input]);
      setInput('');
    }
  };

  return (
    <div>
      <h2>Chat Demo</h2>
      <div style={{border: '1px solid #ccc', minHeight: 100, marginBottom: 8}}>
        {messages.map((msg, i) => <div key={i}>{msg}</div>)}
      </div>
      <input value={input} onChange={e => setInput(e.target.value)} />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
