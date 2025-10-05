import { loader } from 'fumadocs-core/source';
import { createMDXSource } from 'fumadocs-mdx';

export const source = loader({
  baseUrl: '/docs',
  rootDir: 'app/docs',
  source: createMDXSource({
    rootMapPath: 'app/docs',
  }),
});