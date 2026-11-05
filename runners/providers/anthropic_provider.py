"""Claude, via the official Anthropic Python SDK.

Study protocol: one user message, no system prompt, no tools (so no web search), and
provider defaults except for two settings:
  - max_tokens has no default in this API, so it is set high enough not to cut answers off.
  - effort is set to "medium" because that is what the free Claude app showed as its
    default on 2026-11-04 (D24). The API's own default for Sonnet 5.5 is "high", which
    would make the API version think harder than the app a student uses.

Server-side refusal fallbacks are deliberately NOT enabled. They would silently answer
a refused prompt with a different model, and the PRD counts refusals as a result.
"""

import anthropic

MAX_TOKENS = 16000
EFFORT = "medium"
_client = None


def call(model_id: str, prompt: str) -> dict:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    msg = _client.messages.create(
        model=model_id,
        max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT},
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
