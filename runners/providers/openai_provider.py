"""ChatGPT, via the official OpenAI Python SDK (Responses API).

Study protocol: one input message, no instructions (system prompt), no tools (so no
web search), provider defaults for everything else. Each call is a fresh conversation
(no previous_response_id / conversation id).
"""

from openai import OpenAI

_client = None


def call(model_id: str, prompt: str) -> dict:
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from the environment
    resp = _client.responses.create(model=model_id, input=prompt)
    refusal = False
    for item in resp.output or []:
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                refusal = True
    stop = resp.status
    if resp.incomplete_details is not None:
        stop = f"{resp.status}:{resp.incomplete_details.reason}"
    return {
        "raw_text": resp.output_text,
        "model_returned": resp.model,
        "stop_reason": stop,
        "refusal": refusal,
        "usage": resp.usage.model_dump() if resp.usage else None,
        "request_id": resp.id,
    }
