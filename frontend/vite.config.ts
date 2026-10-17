import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Must match FRONTEND_URL in backend/.env: the backend's CORS allow-list and
  // the post-login redirect both point here. strictPort fails loudly instead
  // of silently drifting to 5176 if the port is taken.
  server: { port: 5175, strictPort: true },
})
