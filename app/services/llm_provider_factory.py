from app.core.config import LLM_PROVIDER
from app.core.errors import UnsupportedProviderError
from app.services.fake_llm_provider import FakeLLMProvider
from app.services.gemini_llm_provider import GeminiLLMProvider
from app.services.llm_provider import LLMProvider
from app.services.openai_llm_provider import OpenAILLMProvider


def get_llm_provider() -> LLMProvider:
    if LLM_PROVIDER == "openai":
        return OpenAILLMProvider()
    if LLM_PROVIDER == "gemini":
        return GeminiLLMProvider()
    if LLM_PROVIDER == "fake":
        return FakeLLMProvider()
    raise UnsupportedProviderError(f"Unsupported LLM provider: {LLM_PROVIDER}")
