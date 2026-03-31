import { useState } from 'react';
import MDEditor from '@uiw/react-md-editor';

interface Props {
  initialDraft: string;
  onSend: (body: string) => void;
  onRegenerate: () => void;
  loading: boolean;
}

export default function DraftEditor({ initialDraft, onSend, onRegenerate, loading }: Props) {
  const [value, setValue] = useState(initialDraft);

  return (
    <div style={{ marginTop: '16px', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', background: '#fafafa' }}>
      <h4 style={{ margin: '0 0 8px 0' }}>Draft Reply</h4>
      <MDEditor
        value={value}
        onChange={(val) => setValue(val || '')}
        height={200}
        preview="edit"
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
