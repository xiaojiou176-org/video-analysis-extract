import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [react()],
	test: {
		environment: "jsdom",
		globals: true,
		setupFiles: ["./vitest.setup.ts"],
		include: ["**/__tests__/**/*.{test,spec}.{ts,tsx}", "**/*.{test,spec}.{ts,tsx}"],
		exclude: ["node_modules", ".next", "tests/e2e/**"],
		coverage: {
			provider: "v8",
			reporter: ["text", "json-summary"],
			include: ["components/**/*.tsx", "lib/**/*.ts"],
			exclude: ["**/*.d.ts", "tests/**", "**/__tests__/**", "next-env.d.ts", "lib/api/types.ts"],
			thresholds: {
				lines: 90,
				functions: 90,
				statements: 90,
				branches: 90,
			},
		},
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "."),
		},
	},
});
