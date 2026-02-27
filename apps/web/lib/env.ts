export function getWebActionSessionToken(): string {
	return (process.env.WEB_ACTION_SESSION_TOKEN ?? "").trim();
}
