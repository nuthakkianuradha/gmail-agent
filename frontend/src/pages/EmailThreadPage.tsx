import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchThread } from '../api/emails';
import { generateDraft, sendDraft } from '../api/drafts';
import EmailThread from '../components/EmailThread';
import DraftEditor from '../components/DraftEditor';
import type { Email } from '../types';

export default function EmailThreadPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<string | null>(null);
  const [draftOriginal, setDraftOriginal] = useState<string>('');
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!threadId) return;
    setLoading(true);
    fetchThread(threadId)
      .then((data) => setMessages(data.messages))
      .catch(() => setError('Failed to load thread'))
      .finally(() => setLoading(false));
  }, [threadId]);

  const lastMessage = messages[messages.length - 1];

  const handleGenerate = async () => {
    if (!lastMessage) return;
    setGenerating(true);
    setError(null);
    try {
      const data = await generateDraft(lastMessage.gmail_message_id, lastMessage.gmail_thread_id);
      setDraft(data.draft);
      setDraftOriginal(data.draft);
    } catch {
      setError('Failed to generate draft');
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async (body: string) => {
    if (!lastMessage || !threadId) return;
    setSending(true);
    setError(null);
    try {
      await sendDraft({
        gmail_thread_id: threadId,
        gmail_message_id: lastMessage.gmail_message_id,
        to: lastMessage.from_address,
        subject: lastMessage.subject,
        body,
        draft_before: body !== draftOriginal ? draftOriginal : undefined,
      });
      setSent(true);
      setDraft(null);
    } catch {
      setError('Failed to send email');
    } finally {
      setSending(false);
    }
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}>Loading thread...</div>;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <button onClick={() => navigate('/inbox')} style={{ marginBottom: '16px', padding: '6px 12px', cursor: 'pointer', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}>
        Back to Inbox
      </button>

      {error && <div style={{ padding: '12px', background: '#ffeaea', borderRadius: '4px', marginBottom: '12px' }}>{error}</div>}
      {sent && <div style={{ padding: '12px', background: '#e6f4ea', borderRadius: '4px', marginBottom: '12px' }}>Reply sent successfully!</div>}

      <EmailThread messages={messages} />

      {!draft && !sent && (
        <div style={{ marginTop: '16px', textAlign: 'center' }}>
          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              padding: '10px 24px',
              background: '#1a73e8',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              opacity: generating ? 0.6 : 1,
            }}
          >
            {generating ? 'Generating draft...' : 'Generate Reply'}
          </button>
        </div>
      )}

      {draft && (
        <DraftEditor
          initialDraft={draft}
          onSend={handleSend}
          onRegenerate={handleGenerate}
          loading={sending || generating}
        />
      )}
    </div>
  );
}
