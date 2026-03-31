export default function LoginPage() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '16px' }}>
      <h1 style={{ fontSize: '24px', margin: 0 }}>Gmail Reply Agent</h1>
      <p style={{ color: '#666', margin: 0 }}>AI-powered email replies that learn your style</p>
      <a href={`${API_URL}/auth/login`}>
        <button style={{ padding: '12px 24px', fontSize: '16px', cursor: 'pointer', borderRadius: '4px', border: '1px solid #ddd', background: '#fff' }}>
          Sign in with Google
        </button>
      </a>
    </div>
  );
}
