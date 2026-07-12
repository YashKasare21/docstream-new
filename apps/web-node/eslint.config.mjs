import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Node modules
    "node_modules/**",
    // Minified / vendor files
    "public/*.min.*",
    "public/*.mjs",
    "public/*.js",
    "public/**",
    "**/*.min.js",
    "**/*.min.mjs",
  ]),
]);

export default eslintConfig;
