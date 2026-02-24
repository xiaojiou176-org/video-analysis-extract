import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextCoreWebVitals,
  ...nextTypeScript,
  globalIgnores([".next/**", ".next-e2e-*/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    rules: {
      // App Router layout.tsx uses <head> for Google Fonts - Pages Router rule doesn't apply
      "@next/next/no-page-custom-font": "off",
    },
  },
]);
