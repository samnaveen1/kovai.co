"""
Ollama Client — wraps the local Ollama REST API.
Ollama runs on http://localhost:11434 by default and does NOT require an API key.

Supported models (install with `ollama pull <model>`):
  llama3, llama3.1, mistral, phi3, gemma, gemma2, deepseek-r1, codellama
"""

import json
import urllib.request
import urllib.error
from typing import Optional


class OllamaError(Exception):
    pass


class OllamaClient:
    """
    Thin wrapper around the Ollama /api/generate endpoint.

    Args:
        model:    Ollama model name, e.g. "llama3" (default)
        base_url: Ollama server URL (default: http://localhost:11434)
        timeout:  Request timeout in seconds (default: 120)
    """

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 120,
    ):
        self.model    = model
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout

    # ------------------------------------------------------------------ public
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Send a prompt to Ollama and return the response text.
        Uses streaming=False for simplicity.
        """
        payload: dict = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        url  = f"{self.base_url}/api/generate"
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
                return result.get("response", "").strip()
        except urllib.error.URLError as e:
            raise OllamaError(
                f"Cannot connect to Ollama at {self.base_url}.\n"
                f"Make sure Ollama is running:  ollama serve\n"
                f"Original error: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise OllamaError(f"Invalid JSON from Ollama: {e}") from e

    def is_available(self) -> bool:
        """Return True if Ollama server is reachable."""
        try:
            urllib.request.urlopen(
                f"{self.base_url}/api/tags", timeout=5
            )
            return True
        except Exception:
            return False

    def list_models(self) -> list:
        """Return list of locally available model names."""
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/api/tags", timeout=10
            ) as resp:
                data = json.loads(resp.read().decode())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
