// source.config.ts
import { defineDocs, defineConfig } from "fumadocs-mdx/config/zod-3";
var source_config_default = defineConfig({
  docs: defineDocs({
    dir: "app/docs"
  })
});
export {
  source_config_default as default
};
