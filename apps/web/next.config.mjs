/** @type {import('next').NextConfig} */
const nextConfig = {
	reactStrictMode: true,
	...(process.env.WEB_E2E_NEXT_DIST_DIR
		? { distDir: process.env.WEB_E2E_NEXT_DIST_DIR }
		: {}),
};

export default nextConfig;
