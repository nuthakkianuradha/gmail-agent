import type { EmailSummary } from '../types';

interface Props {
  emails: EmailSummary[];
  onSelect: (email: EmailSummary) => void;
}

export default function EmailList({ emails, onSelect }: Props) {
  if (emails.length === 0) {
    return <p style={{ padding: '20px', color: '#666' }}>No emails found.</p>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', background: '#e0e0e0' }}>
      {emails.map((email) => (
        <div
          key={email.gmail_message_id}
          onClick={() => onSelect(email)}
          style={{
            padding: '12px 16px',
            background: email.is_unread ? '#fff' : '#f8f8f8',
            cursor: 'pointer',
            borderLeft: email.is_unread ? '3px solid #1a73e8' : '3px solid transparent',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <strong style={{ fontSize: '14px', fontWeight: email.is_unread ? 700 : 400 }}>
              {email.from_address}
            </strong>
            <span style={{ fontSize: '12px', color: '#666' }}>
              {email.received_at?.split(',')[0] || ''}
            </span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: email.is_unread ? 600 : 400 }}>
            {email.subject}
          </div>
          <div style={{ fontSize: '13px', color: '#666', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {email.snippet}
          </div>
        </div>
      ))}
    </div>
  );
}
