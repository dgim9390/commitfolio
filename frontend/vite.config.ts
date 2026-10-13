import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // /api 요청은 FastAPI(8000번)로 넘긴다 → 브라우저 입장에선 같은 주소라 CORS 설정이 필요 없다
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
