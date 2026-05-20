"""Hugging Face inference client for migration analysis."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


class HuggingFaceError(Exception):
    pass


class HuggingFaceClient:
    """Thin wrapper around the Hugging Face text-generation inference API."""

    DEFAULT_MODEL = os.getenv(
        "HUGGING_FACE_MODEL",
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
    )
    DEFAULT_API_KEY = os.getenv("HUGGING_FACE_API_KEY", "")

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str = DEFAULT_API_KEY,
        timeout: int = 120,
    ):
        self.model = model
        self.api_key = api_key.strip()
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.api_key:
            raise HuggingFaceError(
                "Missing Hugging Face API key. Set HUGGING_FACE_API_KEY in your environment."
            )

        if system:
            prompt = f"{system}\n\n{prompt}"

        url = f"https://api-inference.huggingface.co/models/{self.model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 1200,
                "temperature": 0.2,
                "return_full_text": False,
            },
            "options": {
                "wait_for_model": True,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
        except urllib.error.URLError as e:
            raise HuggingFaceError(
                "Cannot connect to Hugging Face inference API. Check your network and API key."
            ) from e
        except json.JSONDecodeError as e:
            raise HuggingFaceError(f"Invalid JSON from Hugging Face: {e}") from e

        if isinstance(result, dict) and result.get("error"):
            raise HuggingFaceError(result["error"])

        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                if "generated_text" in first:
                    return str(first["generated_text"]).strip()
                if "summary_text" in first:
                    return str(first["summary_text"]).strip()

        if isinstance(result, dict) and "generated_text" in result:
            return str(result["generated_text"]).strip()

        raise HuggingFaceError("Unexpected response format from Hugging Face inference API.")
