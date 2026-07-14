from __future__ import annotations
import json
import time
import asyncio
import threading
from typing import Any, Dict, Optional

from keystore import get_keystore


class BrowserAuthManager:
    def __init__(self) -> None:
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._playwright_browser = None
        self._playwright_context = None

    def get_auth_status(self, provider_id: str) -> Dict[str, Any]:
        ks = get_keystore()
        token = ks.get_key(provider_id, "browser_token")
        if token:
            session = self._active_sessions.get(provider_id, {})
            expires = session.get("expires_at", 0)
            if expires and time.time() > expires:
                return {"authenticated": True, "expired": True, "provider": provider_id, "message": "Token expired, re-login needed"}
            method = session.get("method", "unknown")
            return {"authenticated": True, "expired": False, "provider": provider_id, "auth_method": method, "message": f"Authenticated via browser login ({method})"}
        api_key = ks.get_key(provider_id, "api_key")
        if api_key:
            return {"authenticated": True, "expired": False, "provider": provider_id, "auth_method": "api_key", "message": "Authenticated via API key"}
        return {"authenticated": False, "provider": provider_id, "message": "Not authenticated"}

    def start_browser_login(self, provider_id: str) -> Dict[str, Any]:
        from config import DEFAULT_PROVIDERS
        cfg = next((p for p in DEFAULT_PROVIDERS if p["id"] == provider_id), None)
        if not cfg:
            return {"success": False, "error": f"Unknown provider: {provider_id}"}
        if not cfg.get("supports_browser_login"):
            return {"success": False, "error": f"{provider_id} does not support browser login"}

        login_type = cfg.get("browser_login_type", "web_session")

        if provider_id == "openai":
            if login_type == "oauth":
                return self._start_openai_oauth(cfg)
            else:
                return self._start_playwright_session(provider_id, cfg)
        elif provider_id == "deepseek":
            return self._start_playwright_session(provider_id, cfg)

        return self._start_playwright_session(provider_id, cfg)

    def _start_openai_oauth(self, cfg: Dict) -> Dict[str, Any]:
        try:
            import httpx
            import secrets
            import webbrowser

            state = secrets.token_urlsafe(32)
            self._active_sessions["openai"] = {
                "state": state,
                "status": "pending",
                "started_at": time.time(),
                "method": "oauth",
            }

            auth_url = f"https://auth0.openai.com/authorize?client_id=RWO5MoAq9M1S0s1B9vEI5pP3HdSZz12G&redirect_uri=http://localhost:18900/auth/callback/openai&response_type=code&scope=openid%20email%20profile&state={state}"

            webbrowser.open(auth_url)

            return {
                "success": True,
                "auth_url": auth_url,
                "message": "Browser opened. Complete the login and authorize the app. The token will be captured automatically via the callback endpoint.",
                "provider": "openai",
                "method": "oauth",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _start_playwright_session(self, provider_id: str, cfg: Dict) -> Dict[str, Any]:
        try:
            self._active_sessions[provider_id] = {
                "status": "playwright_pending",
                "started_at": time.time(),
                "method": "web_session",
            }

            thread = threading.Thread(
                target=self._run_playwright_login,
                args=(provider_id, cfg),
                daemon=True,
            )
            thread.start()

            return {
                "success": True,
                "message": f"Browser window opening for {provider_id}. Complete the login — token will be captured automatically.",
                "provider": provider_id,
                "method": "web_session",
                "experimental": True,
                "warning": "Web-session login is unofficial and may break when the provider changes their site. API-key auth is the reliable default.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_playwright_login(self, provider_id: str, cfg: Dict) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_playwright_login(provider_id, cfg))
            loop.close()
        except Exception as e:
            self._active_sessions[provider_id] = {
                "status": "error",
                "error": str(e),
                "method": "web_session",
            }

    async def _async_playwright_login(self, provider_id: str, cfg: Dict) -> None:
        from playwright.async_api import async_playwright

        login_urls = {
            "openai": "https://chatgpt.com",
            "deepseek": "https://chat.deepseek.com/sign_in",
        }

        session_token_names = {
            "openai": "__Secure-next-auth.session-token",
            "deepseek": "ds_chat_web",
        }

        url = login_urls.get(provider_id, cfg.get("login_url", ""))
        token_name = session_token_names.get(provider_id, "session_token")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(url)

            await page.wait_for_url("**", timeout=300000)

            page_url = page.url
            is_logged_in = any(indicator in page_url.lower() for indicator in ["chat", "app", "dashboard", "inbox"])

            if not is_logged_in:
                for _ in range(600):
                    await asyncio.sleep(0.5)
                    page_url = page.url
                    is_logged_in = any(indicator in page_url.lower() for indicator in ["chat", "app", "dashboard", "inbox"])
                    if is_logged_in:
                        break

            if is_logged_in:
                cookies = await context.cookies()
                token_value = None
                for cookie in cookies:
                    if cookie["name"] == token_name:
                        token_value = cookie["value"]
                        break
                if not token_value and cookies:
                    token_value = json.dumps({c["name"]: c["value"] for c in cookies})

                if token_value:
                    ks = get_keystore()
                    ks.add_key(provider_id, token_value, "browser_token")
                    self._active_sessions[provider_id] = {
                        "status": "authenticated",
                        "expires_at": time.time() + 86400,
                        "method": "web_session",
                    }
                else:
                    self._active_sessions[provider_id] = {
                        "status": "error",
                        "error": "Could not extract session token from cookies",
                        "method": "web_session",
                    }
            else:
                self._active_sessions[provider_id] = {
                    "status": "error",
                    "error": "Login timeout — did not detect successful login",
                    "method": "web_session",
                }

            await browser.close()

    def complete_oauth_callback(self, provider_id: str, code: str, state: str) -> Dict[str, Any]:
        session = self._active_sessions.get(provider_id, {})
        if session.get("state") != state:
            return {"success": False, "error": "Invalid state parameter"}

        if provider_id == "openai":
            try:
                import httpx
                resp = httpx.post("https://auth0.openai.com/oauth/token", data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": "RWO5MoAq9M1S0s1B9vEI5pP3HdSZz12G",
                    "redirect_uri": "http://localhost:18900/auth/callback/openai",
                })
                if resp.status_code == 200:
                    token_data = resp.json()
                    access_token = token_data.get("access_token")
                    if access_token:
                        ks = get_keystore()
                        ks.add_key("openai", access_token, "browser_token")
                        self._active_sessions["openai"]["status"] = "authenticated"
                        self._active_sessions["openai"]["expires_at"] = time.time() + token_data.get("expires_in", 3600)
                        self._active_sessions["openai"]["method"] = "oauth"
                        return {"success": True, "message": "OpenAI browser login successful"}
                return {"success": False, "error": f"OAuth token exchange failed: {resp.text[:200]}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Unknown provider: {provider_id}"}

    def save_manual_token(self, provider_id: str, token: str) -> Dict[str, Any]:
        ks = get_keystore()
        ks.add_key(provider_id, token, "browser_token")
        self._active_sessions[provider_id] = {
            "status": "authenticated",
            "expires_at": 0,
            "method": "manual",
        }
        return {"success": True, "message": f"Token saved for {provider_id}"}

    def logout(self, provider_id: str) -> Dict[str, Any]:
        ks = get_keystore()
        ks.remove_key(provider_id, "browser_token")
        if provider_id in self._active_sessions:
            del self._active_sessions[provider_id]
        return {"success": True, "message": f"Logged out from {provider_id}"}

    def get_login_status(self, provider_id: str) -> Dict[str, Any]:
        session = self._active_sessions.get(provider_id, {})
        return {
            "provider": provider_id,
            "status": session.get("status", "unknown"),
            "method": session.get("method", ""),
            "error": session.get("error", ""),
        }


_browser_auth = BrowserAuthManager()


def get_browser_auth() -> BrowserAuthManager:
    return _browser_auth
