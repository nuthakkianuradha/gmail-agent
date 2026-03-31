import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { fetchInbox } from '../api/emails';
import EmailList from '../components/EmailList';
import type { EmailSummary } from '../types';

export default function InboxPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInbox = async (pageToken?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInbox(pageToken);
      if (pageToken) {
        setEmails((prev) => [...prev, ...data.emails]);
      } else {
        setEmails(data.emails);
      }
      setNextPageToken(data.next_page_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load inbox');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInbox();
  }, []);

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ margin: 0, fontSize: '20px' }}>Inbox</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={() => navigate('/settings')} style={{ padding: '6px 12px', cursor: 'pointer', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}>
            Settings
          </button>
          <span style={{ fontSize: '14px', color: '#666' }}>{user?.email}</span>
          <button onClick={logout} style={{ padding: '6px 12px', cursor: 'pointer', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}>
            Logout
          </button>
        </div>
      </div>

      {error && <div style={{ padding: '12px', background: '#ffeaea', borderRadius: '4px', marginBottom: '12px' }}>{error}</div>}

      <EmailList
        emails={emails}
        onSelect={(email) => navigate(`/email/${email.gmail_thread_id}`)}
      />

      {loading && <p style={{ textAlign: 'center', padding: '20px' }}>Loading...</p>}

      {!loading && nextPageToken && (
        <div style={{ textAlign: 'center', padding: '16px' }}>
          <button onClick={() => loadInbox(nextPageToken)} style={{ padding: '8px 20px', cursor: 'pointer', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}>
            Load More
          </button>
        </div>
      )}
    </div>
  );
}
