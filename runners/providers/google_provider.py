"""Gemini, via the official Google Gen AI Python SDK (google-genai).

Study protocol: one user message, no system instruction, no tools (Google Search
grounding is off unless requested), provider defaults for everything else.
"""

from google import genai

_client = None
BLOCK_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "IMAGE_SAFETY"}


def call(model_id: str, prompt: str) -> dict:
    global _client
    if _client is None:
        _client = genai.Client()  # reads GEMINI_API_KEY from the environment
    resp = _client.models.generate_content(model=model_id, contents=prompt)

    finish = None
    text = ""
    if resp.candidates:
        cand = resp.candidates[0]
        finish = getattr(cand.finish_reason, "name", str(cand.finish_reason)) if cand.finish_reason else None
        parts = (cand.content.parts if cand.content and cand.content.parts else [])
        text = "".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False))
    blocked_prompt = bool(resp.prompt_feedback and resp.prompt_feedback.block_reason)
    return {
        "raw_text": text,
        "model_returned": resp.model_version,
        "stop_reason": finish or ("PROMPT_BLOCKED" if blocked_prompt else None),
        "refusal": blocked_prompt or (finish in BLOCK_REASONS),
        "usage": resp.usage_metadata.model_dump() if resp.usage_metadata else None,
        "request_id": resp.response_id,
    }
