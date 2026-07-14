from __future__ import annotations
from typing import Any, Dict, Optional

from keystore import get_keystore


def test_provider_key(provider_id: str, model: str, base_url: Optional[str] = None, use_browser_token: bool = False) -> Dict[str, Any]:
    from providers import get_provider
    provider = get_provider(provider_id, base_url=base_url, use_browser_token=use_browser_token)
    return provider.test_connection(model)


def test_tavily_key() -> Dict[str, Any]:
    ks = get_keystore()
    key = ks.get_search_key("tavily")
    if not key:
        return {"success": False, "error": "No Tavily key configured"}
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        result = client.search("test query", max_results=1)
        return {"success": True, "response": f"Tavily OK - {len(result.get('results', []))} results"}
    except ImportError:
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": "test", "max_results": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                return {"success": True, "response": "Tavily key is valid"}
            return {"success": False, "error": f"Tavily returned status {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_brave_key() -> Dict[str, Any]:
    ks = get_keystore()
    key = ks.get_search_key("brave")
    if not key:
        return {"success": False, "error": "No Brave key configured"}
    try:
        import requests
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
            params={"q": "test", "count": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"success": True, "response": "Brave key is valid"}
        return {"success": False, "error": f"Brave returned status {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
