const API_BASE = "http://127.0.0.1:18900";
const WS_BASE = "ws://127.0.0.1:18900/ws";

export async function apiGet(path: string): Promise<any> {
  const resp = await fetch(`${API_BASE}${path}`);
  return resp.json();
}

export const post = apiPost;

export async function getSearchKeys(): Promise<any> {
  return apiGet("/search-keys");
}

export async function apiPost(path: string, body?: any): Promise<any> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return resp.json();
}

export async function apiDelete(path: string): Promise<any> {
  const resp = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  return resp.json();
}

export function createWebSocket(): WebSocket {
  return new WebSocket(WS_BASE);
}

export function createTerminalWs(): WebSocket {
  return new WebSocket("ws://127.0.0.1:18900/ws/terminal");
}

export async function connectWorkspace(path: string): Promise<any> {
  return apiPost("/workspace/connect", { path });
}

export async function getProviders(): Promise<any> {
  return apiGet("/providers");
}

export async function getModels(provider: string, freeOnly: boolean = false): Promise<any> {
  return apiGet(`/models?provider=${provider}&free_only=${freeOnly}`);
}

export async function saveKey(providerId: string, key: string, keyType: string = "api_key"): Promise<any> {
  return apiPost("/keys", { provider_id: providerId, key, key_type: keyType });
}

export async function saveSearchKey(backend: string, key: string): Promise<any> {
  return apiPost("/search-keys", { backend, key });
}

export async function testProvider(providerId: string, model: string): Promise<any> {
  return apiPost("/api-check", { provider_id: providerId, model });
}

export async function testTavily(): Promise<any> {
  return apiPost("/api-check/tavily");
}

export async function testBrave(): Promise<any> {
  return apiPost("/api-check/brave");
}

export async function getSandboxStatus(): Promise<any> {
  return apiGet("/sandbox/status");
}

export async function startSandbox(): Promise<any> {
  return apiPost("/sandbox/start");
}

export async function stopSandbox(): Promise<any> {
  return apiPost("/sandbox/stop");
}

export async function startBrowserLogin(providerId: string): Promise<any> {
  return apiPost("/auth/browser-login", { provider_id: providerId });
}

export async function getAuthStatus(providerId: string): Promise<any> {
  return apiGet(`/auth/status?provider_id=${providerId}`);
}

export async function saveManualToken(providerId: string, token: string): Promise<any> {
  return apiPost("/auth/manual-token", { provider_id: providerId, token });
}

export async function logoutProvider(providerId: string): Promise<any> {
  return apiPost(`/auth/logout?provider_id=${providerId}`);
}

export async function getWorkspaceTree(): Promise<any> {
  return apiGet("/workspace/tree");
}

export async function getWorkspaceStatus(): Promise<any> {
  return apiGet("/workspace/status");
}

export async function getGitStatus(): Promise<any> {
  return apiGet("/git/status");
}

export async function getGitLog(count: number = 10): Promise<any> {
  return apiGet(`/git/log?count=${count}`);
}

export async function getGitDiff(filePath?: string): Promise<any> {
  const q = filePath ? `?file_path=${encodeURIComponent(filePath)}` : "";
  return apiGet(`/git/diff${q}`);
}

export async function gitCommit(message: string): Promise<any> {
  return apiPost("/git/commit", { message });
}

export async function gitInit(): Promise<any> {
  return apiPost("/git/init", {});
}

export async function getGitBranches(): Promise<any> {
  return apiGet("/git/branch");
}

export async function getSessions(): Promise<any> {
  return apiGet("/sessions");
}

export async function saveSession(sessionId: string, task: string, provider: string, model: string): Promise<any> {
  return apiPost("/sessions/save", { session_id: sessionId, task, provider, model });
}

export async function loadSession(sessionId: string): Promise<any> {
  return apiPost(`/sessions/load/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<any> {
  return apiDelete(`/sessions/${sessionId}`);
}

export async function getStats(): Promise<any> {
  return apiGet("/stats");
}

export async function computeDiff(oldContent: string, newContent: string, filePath: string): Promise<any> {
  return apiPost("/diff", { old_content: oldContent, new_content: newContent, file_path: filePath });
}

export function downloadExport(): void {
  window.open(`${API_BASE}/export`, "_blank");
}
