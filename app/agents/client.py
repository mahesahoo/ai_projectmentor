from google import genai

# gemini-3.5-flash is on Gemini's free tier (see ai.google.dev/gemini-api/docs/pricing) -
# chosen so the pipeline can be validated and demoed without a paid API key.
MODEL = "gemini-3.5-flash"

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Lazily constructs the Gemini client on first use, not at import time.

    genai.Client() raises immediately if GEMINI_API_KEY/GOOGLE_API_KEY isn't
    set (unlike anthropic.Anthropic(), which defers that check to the first
    API call). Constructing it at module import time would crash the whole
    app - including the Milestone 1 routes that need no LLM at all - just
    because the key isn't configured yet. Deferring construction means the
    app boots fine either way, and only the agent pipeline fails (caught by
    pipeline.py's broad except) when an idea is actually submitted without
    a key configured.
    """
    global _client
    if _client is None:
        _client = genai.Client()
    return _client
