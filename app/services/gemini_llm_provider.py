from google import genai
from google.genai import errors as genai_errors

from app.core.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL
from app.core.errors import LLMProviderError, MissingApiKeyError
from app.domain.models import SearchResult
from app.services.rag_prompt import SYSTEM_PROMPT, build_user_prompt


class GeminiLLMProvider:
    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise MissingApiKeyError("GEMINI_API_KEY is not configured")
        self._client = genai.Client(api_key=GEMINI_API_KEY)

    def generate_answer(self, question: str, context_chunks: list[SearchResult]) -> str:
        prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(question, context_chunks)}"
        try:
            response = self._client.models.generate_content(
                model=GEMINI_CHAT_MODEL,
                contents=prompt,
            )
        except genai_errors.ClientError as error:
            raise LLMProviderError(
                f"Gemini chat request failed: {error}",
                status_code=getattr(error, "code", None) or 502,
            ) from error

        text = response.text
        if not text:
            raise LLMProviderError(
                "Gemini chat completion returned an empty response.",
                status_code=502,
            )
        return text
