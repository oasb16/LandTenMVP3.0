'use client';

/* eslint-disable @typescript-eslint/no-explicit-any */

import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Bot, User, MessageSquare } from 'lucide-react';
import { useStreamChat } from '@/hooks/chat/StreamChatContext';

interface Message {
  id: string;
  text: string;
  user: {
    id: string;
    name: string;
  };
  created_at: Date;
  isAI?: boolean;
}

interface PropertyAIChatProps {
  persona: string;
  userId?: string;
}

export default function PropertyAIChat({ persona, userId }: PropertyAIChatProps) {
  // Use shared StreamChat context instead of creating own client
  const {
    client,
    activeChannel,
    messages: contextMessages,
    loading,
    error,
    sendMessage: contextSendMessage
  } = useStreamChat();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Sync messages from context
  useEffect(() => {
    if (contextMessages && contextMessages.length > 0) {
      const formattedMessages = contextMessages.map((msg: any) => ({
        id: msg.id || `${msg.cid}-${Date.now()}`,
        text: msg.text || '',
        user: {
          id: msg.user?.id || 'unknown',
          name: msg.user?.name || 'Unknown',
        },
        created_at: msg.created_at ? new Date(msg.created_at) : new Date(),
        isAI: msg.user?.id?.includes('agent') || msg.user?.id?.includes('bot') || msg.user?.id?.startsWith('ai-'),
      }));
      setMessages(formattedMessages);
    }
  }, [contextMessages]);

  const handleSend = async () => {
    if (!inputValue.trim() || !client || !activeChannel || sending) return;

    setSending(true);
    try {
      await contextSendMessage(inputValue.trim());
      setInputValue('');
    } catch (err) {
      console.error('Send message error:', err);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center">
        <div className="text-red-500 mb-2">Chat unavailable</div>
        <div className="text-sm text-gray-600">{error}</div>
      </div>
    );
  }

  if (!client || !activeChannel) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-sm text-gray-400">Connecting to chat...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <MessageSquare className="w-12 h-12 mb-2 opacity-50" />
            <p>No messages yet</p>
            <p className="text-xs mt-1">Start a conversation!</p>
          </div>
        )}

        {messages.map((message) => {
          const isOwnMessage = message.user.id === userId || message.user.id === client?.userID;

          return (
            <div
              key={message.id}
              className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[80%] ${isOwnMessage ? 'order-2' : 'order-1'}`}>
                {!isOwnMessage && (
                  <div className="flex items-center gap-2 mb-1">
                    {message.isAI ? (
                      <Bot className="w-4 h-4 text-purple-600" />
                    ) : (
                      <User className="w-4 h-4 text-gray-600" />
                    )}
                    <span className="text-xs font-medium text-gray-700">
                      {message.user.name}
                    </span>
                  </div>
                )}
                <div
                  className={`rounded-2xl px-4 py-2 ${
                    isOwnMessage
                      ? 'bg-blue-600 text-white'
                      : message.isAI
                      ? 'bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 text-gray-800'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap break-words">{message.text}</p>
                </div>
                <div className={`text-xs text-gray-400 mt-1 ${isOwnMessage ? 'text-right' : 'text-left'}`}>
                  {message.created_at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-3 bg-gray-50">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            className="flex-1 bg-white border border-gray-300 rounded-full px-4 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            disabled={sending || !activeChannel}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || sending || !activeChannel}
            className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? (
              <Loader2 className="w-5 h-5 text-white animate-spin" />
            ) : (
              <Send className="w-5 h-5 text-white" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
