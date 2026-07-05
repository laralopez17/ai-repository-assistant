from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL
from app.core.errors import MissingApiKeyError


class GeminiEmbeddingProvider:
    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            raise MissingApiKeyError("GEMINI_API_KEY is not configured")
        self._client = genai.Client(api_key=GEMINI_API_KEY)

    @property
    def model_name(self) -> str:
        return GEMINI_EMBEDDING_MODEL

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        contents = [types.Content(parts=[types.Part(text=text)]) for text in texts]
        response = self._client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=contents,
        )
        return [list(embedding.values) for embedding in response.embeddings]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
