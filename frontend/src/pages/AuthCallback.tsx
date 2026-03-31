import { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

export default function AuthCallback() {
  const { setToken, fetchUser } = useAuthStore();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      setToken(token);
      fetchUser().then(() => {
        window.location.href = '/inbox';
      });
    }
  }, [setToken, fetchUser]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      Authenticating...
    </div>
  );
}
