"""Claude, via the official Anthropic Python SDK.

Study protocol: one user message, no system prompt, provider defaults for everything
else. That means no thinking/effort/temperature settings and no tools (so no web search).
max_tokens has no default in this API, so it is set high enough not to cut answers off.

Server-side refusal fallbacks are deliberately NOT enabled. They would silently answer
a refused prompt with a different model, and the PRD counts refusals as a result.
"""

import anthropic

MAX_TOKENS = 16000
_client = None


def call(model_id: str, prompt: str) -> dict:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    msg = _client.messages.create(
        model=model_id,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    return {
        "raw_text": text,
        "model_returned": msg.model,
        "stop_reason": msg.stop_reason,
        "refusal": msg.stop_reason == "refusal",
        "usage": msg.to_dict().get("usage"),
        "request_id": getattr(msg, "_request_id", None) or msg.id,
    }
