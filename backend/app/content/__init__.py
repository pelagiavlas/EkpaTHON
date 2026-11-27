import os

from app.content.provider import ContentProvider, SectionInput


def get_provider() -> ContentProvider:
    """CONTENT_PROVIDER=mock (default) or llm."""
    choice = os.getenv("CONTENT_PROVIDER", "mock").lower()
    if choice == "llm":
        from app.content.llm import LLMProvider

        return LLMProvider()
    from app.content.mock import MockProvider

    return MockProvider()
