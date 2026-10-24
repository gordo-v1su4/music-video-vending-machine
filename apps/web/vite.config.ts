import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
// /pilot-api is the local take-review server (scripts/mvvm_gen/review_server.py).
const pilotApi = { '/pilot-api': 'http://127.0.0.1:5197' };
export default defineConfig({
  plugins: [sveltekit()],
  server: { port: 5198, strictPort: true, proxy: pilotApi },
  preview: { proxy: pilotApi }
});
