import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  resolve: {
    alias: mode === 'test' ? { antd: 'antd/lib/index.js' } : undefined,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    testTimeout: 60000,
    deps: {
      optimizer: {
        web: {
          include: ['@ant-design/icons', '@ant-design/colors', '@ant-design/icons-svg'],
        },
      },
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html'],
      reportsDirectory: './coverage',
    },
  },
}))
