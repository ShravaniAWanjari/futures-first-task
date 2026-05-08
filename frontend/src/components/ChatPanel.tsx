import { useRef, useEffect } from 'react';
import type { Message } from '../types';
import MessageBubble from './MessageBubble';

interface ChatPanelProps {
  messages: Message[];
  queryLoading: boolean;
  onOpenSources: (trace?: any) => void;
}

export default function ChatPanel({ messages, queryLoading, onOpenSources }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, queryLoading]);

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '32px 40px' }}>
      <div style={{ maxWidth: 660, margin: '0 auto' }}>
        {messages.map((msg, idx) => (
          <MessageBubble key={msg.id || idx} message={msg} onOpenSources={onOpenSources} />
        ))}
        {queryLoading && (
          <div className="animate-fade-in" style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="skeleton" style={{ height: 14, width: '65%' }}></div>
              <div className="skeleton" style={{ height: 14, width: '40%' }}></div>
              <div className="skeleton" style={{ height: 14, width: '52%' }}></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
