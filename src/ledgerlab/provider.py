"""OpenAI-compatible adapter. Tests inject an opener. No network in CI."""

from __future__ import annotations

import json
import urllib.request

from ledgerlab.model import Completion, ToolCall


class OpenAICompatibleClient:
    name = "openai-compatible"

    def __init__(self, api_key: str, base_url: str, model: str, opener=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.opener = opener or urllib.request.urlopen

    def complete(self, messages, tools=None, temperature=0, response_schema=None) -> Completion:
        body: dict = {
            "model": self.model_name,
            "temperature": temperature,
            "messages": messages,
        }
        if tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
        if response_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": response_schema}
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self.opener(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        message = payload["choices"][0]["message"]
        calls = []
        for raw in message.get("tool_calls") or []:
            arguments = raw["function"]["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            calls.append(ToolCall(raw["function"]["name"], arguments))
        usage = payload.get("usage") or {}
        return Completion(
            content=message.get("content") or "",
            tool_calls=calls,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            model=self.model_name if self.model_name in ("fake-primary", "fake-fallback") else "openai-compatible",
        )
