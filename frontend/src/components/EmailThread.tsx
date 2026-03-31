import type { Email } from '../types';

interface Props {
  messages: Email[];
}

export default function EmailThread({ messages }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {messages.map((msg, idx) => (
        <div
          key={msg.gmail_message_id}
          style={{
            padding: '16px',
            background: '#fff',
            border: '1px solid #e0e0e0',
            borderRadius: '8px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <strong>{msg.from_address}</strong>
            <span style={{ fontSize: '12px', color: '#666' }}>{msg.received_at}</span>
          </div>
          {idx === 0 && (
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>{msg.subject}</h3>
          )}
          <div style={{ fontSize: '14px', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
            {msg.body_text}
          </div>
        </div>
      ))}
    </div>
  );
}
