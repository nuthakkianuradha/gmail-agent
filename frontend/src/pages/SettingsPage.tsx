import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchPersona, savePersona, fetchRules, createRule, deleteRule } from '../api/settings';
import type { Persona, Rule } from '../types';

export default function SettingsPage() {
  const navigate = useNavigate();
  const [persona, setPersona] = useState<Persona>({
    display_name: '',
    tone: 'professional',
    style_notes: '',
    signature: '',
    language: 'en',
    custom_instructions: '',
  });
  const [rules, setRules] = useState<Rule[]>([]);
  const [newRule, setNewRule] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchPersona().then((p) => { if (p) setPersona(p); });
    fetchRules().then(setRules);
  }, []);

  const handleSavePersona = async () => {
    setSaving(true);
    try {
      const saved = await savePersona(persona);
      setPersona(saved);
      setMessage('Persona saved!');
      setTimeout(() => setMessage(null), 2000);
    } catch {
      setMessage('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleAddRule = async () => {
    if (!newRule.trim()) return;
    try {
      const rule = await createRule(newRule.trim());
      setRules((prev) => [...prev, rule]);
      setNewRule('');
    } catch {
      setMessage('Failed to add rule');
    }
  };

  const handleDeleteRule = async (id: string) => {
    try {
      await deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setMessage('Failed to delete rule');
    }
  };

  const inputStyle = { width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '14px', boxSizing: 'border-box' as const };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
      <button onClick={() => navigate('/inbox')} style={{ marginBottom: '16px', padding: '6px 12px', cursor: 'pointer', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}>
        Back to Inbox
      </button>

      {message && <div style={{ padding: '8px 12px', background: '#e6f4ea', borderRadius: '4px', marginBottom: '12px' }}>{message}</div>}

      <h2 style={{ fontSize: '18px' }}>Persona</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
        <div>
          <label style={{ fontSize: '13px', fontWeight: 600 }}>Display Name</label>
          <input style={inputStyle} value={persona.display_name} onChange={(e) => setPersona({ ...persona, display_name: e.target.value })} placeholder="How you want to be addressed" />
        </div>
        <div>
          <label style={{ fontSize: '13px', fontWeight: 600 }}>Tone</label>
          <select style={inputStyle} value={persona.tone} onChange={(e) => setPersona({ ...persona, tone: e.target.value })}>
            <option value="professional">Professional</option>
            <option value="casual">Casual</option>
            <option value="friendly">Friendly</option>
            <option value="formal">Formal</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: '13px', fontWeight: 600 }}>Style Notes</label>
          <textarea style={{ ...inputStyle, minHeight: '60px' }} value={persona.style_notes} onChange={(e) => setPersona({ ...persona, style_notes: e.target.value })} placeholder="e.g., Keep it concise, use bullet points..." />
        </div>
        <div>
          <label style={{ fontSize: '13px', fontWeight: 600 }}>Signature</label>
          <textarea style={{ ...inputStyle, minHeight: '60px' }} value={persona.signature} onChange={(e) => setPersona({ ...persona, signature: e.target.value })} placeholder="e.g., Best regards,&#10;John" />
        </div>
        <div>
          <label style={{ fontSize: '13px', fontWeight: 600 }}>Custom Instructions</label>
          <textarea style={{ ...inputStyle, minHeight: '80px' }} value={persona.custom_instructions} onChange={(e) => setPersona({ ...persona, custom_instructions: e.target.value })} placeholder="e.g., Never use exclamation marks, always CC my assistant..." />
        </div>
        <button onClick={handleSavePersona} disabled={saving} style={{ padding: '8px 20px', background: '#1a73e8', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', alignSelf: 'flex-start' }}>
          {saving ? 'Saving...' : 'Save Persona'}
        </button>
      </div>

      <h2 style={{ fontSize: '18px' }}>Rules</h2>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input style={{ ...inputStyle, flex: 1 }} value={newRule} onChange={(e) => setNewRule(e.target.value)} placeholder="e.g., Always be formal with clients" onKeyDown={(e) => e.key === 'Enter' && handleAddRule()} />
        <button onClick={handleAddRule} style={{ padding: '8px 16px', background: '#1a73e8', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', whiteSpace: 'nowrap' }}>
          Add Rule
        </button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {rules.map((rule) => (
          <div key={rule.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8f8f8', borderRadius: '4px' }}>
            <span style={{ fontSize: '14px' }}>{rule.rule_text}</span>
            <button onClick={() => handleDeleteRule(rule.id)} style={{ padding: '4px 8px', background: 'none', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer', color: '#c00' }}>
              Delete
            </button>
          </div>
        ))}
        {rules.length === 0 && <p style={{ color: '#666', fontSize: '14px' }}>No rules yet.</p>}
      </div>
    </div>
  );
}
