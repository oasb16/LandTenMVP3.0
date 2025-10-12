import React from 'react';
import Chat from '../components/Chat';

export default function Home() {
  // TODO: Replace with real auth/user context
  const user = { id: 'demo', role: 'tenant' };
  return (
    <div>
      <h1>LandTen MVP Chat</h1>
      <Chat user={user} />
    </div>
  );
}
