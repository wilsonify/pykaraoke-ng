import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      // Make imports from tests/web resolve into src/web/src.
      '../src/web/src': path.resolve(__dirname, '../../src/web/src'),
    },
  },
});
