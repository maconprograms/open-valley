import { defineDocs, defineConfig } from 'fumadocs-mdx/config';

export default defineConfig({
  docs: defineDocs({
    dir: 'app/docs',
  }),
});