import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextCoreWebVitals,
  ...nextTypeScript,
  globalIgnores([".next/**", ".next-e2e-*/**", "out/**", "build/**", "next-env.d.ts"]),
  {
    files: ["**/*.{test,spec}.{ts,tsx}", "**/__tests__/**/*.{ts,tsx}"],
    rules: {
      // expect-expect equivalent: each test case must include an explicit expect call.
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "CallExpression[callee.name=/^(it|test)$/] > :matches(ArrowFunctionExpression, FunctionExpression) > BlockStatement:not(:has(CallExpression[callee.name='expect']))",
          message: "Each test must contain at least one explicit expect assertion.",
        },
        {
          selector:
            ":matches(IfStatement, ConditionalExpression, SwitchCase, CatchClause) CallExpression[callee.name='expect']",
          message: "Avoid conditional expect assertions to prevent false-green tests.",
        },
      ],
    },
  },
  {
    rules: {
      // App Router layout.tsx uses <head> for Google Fonts - Pages Router rule doesn't apply
      "@next/next/no-page-custom-font": "off",
    },
  },
]);
