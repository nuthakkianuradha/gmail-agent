import { useEffect, useState } from 'react';

interface Props {
  initialDraft: string;
  onSend: (body: string) => void;
  onRegenerate: () => void;
  loading: boolean;
}

/**
 * One plain, always-editable text area for the draft reply.
 * No preview/split modes: what you see is exactly the text that will be sent.
 */
export default function DraftEditor({ initialDraft, onSend, onRegenerate, loading }: Props) {
  const [value, setValue] = useState(initialDraft);

  // Regenerate replaces the draft; reflect the new text in the editor.
  useEffect(() => {
    setValue(initialDraft);
  }, [initialDraft]);

  return (
    <div style={{ marginTop: '16px', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', background: '#fafafa' }}>
      <h4 style={{ margin: '0 0 8px 0' }}>Draft Reply</h4>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={loading}
        spellCheck
        style={{
          display: 'block',
          width: '100%',
          minHeight: '240px',
          boxSizing: 'border-box',
          padding: '12px',
          font: 'inherit',
          fontSize: '16px',
          lineHeight: 1.5,
          color: '#1f1f1f',
          background: '#fff',
          border: '1px solid #ccc',
          borderRadius: '6px',
          resize: 'vertical',
          textAlign: 'left',
          whiteSpace: 'pre-wrap',
        }}
      />
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button
          onClick={() => onSend(value)}
          disabled={loading || !value.trim()}
          style={{
            padding: '8px 20px',
            background: '#1a73e8',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
        <button
          onClick={onRegenerate}
          disabled={loading}
          style={{
            padding: '8px 20px',
            background: '#fff',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Regenerate
        </button>
      </div>
    </div>
  );
}
