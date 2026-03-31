import { create } from 'zustand';
import type { User } from '../types';
import client from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  setToken: (token: string) => void;
  fetchUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  loading: false,

  setToken: (token: string) => {
    localStorage.setItem('token', token);
    set({ token });
  },

  fetchUser: async () => {
    set({ loading: true });
    try {
      const { data } = await client.get<User>('/auth/me');
      set({ user: data, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },
}));
