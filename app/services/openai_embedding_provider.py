from openai import APIStatusError, OpenAI, RateLimitError

from app.core.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
from app.core.errors import EmbeddingProviderError, MissingApiKeyError

_OPENAI_QUOTA_MESSAGE = (
    "OpenAI quota or billing limit exceeded. "
    "Check your OpenAI account billing settings."
)
_OPENAI_RATE_LIMIT_MESSAGE = (
    "OpenAI rate limit exceeded. Try again later."
)


class OpenAIEmbeddingProvider:
    @property
    def model_name(self) -> str:
        return OPENAI_EMBEDDING_MODEL

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not OPENAI_API_KEY:
            raise MissingApiKeyError("OPENAI_API_KEY is not configured")

        if not texts:
            return []

        client = OpenAI(api_key=OPENAI_API_KEY)
        try:
            response = client.embeddings.create(
                input=texts,
                model=OPENAI_EMBEDDING_MODEL,
            )
        except RateLimitError as error:
            raise self._map_rate_limit_error(error) from error
        except APIStatusError as error:
            raise self._map_api_status_error(error) from error

        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def _map_rate_limit_error(self, error: RateLimitError) -> EmbeddingProviderError:
        if self._is_quota_error(error):
            return EmbeddingProviderError(_OPENAI_QUOTA_MESSAGE, status_code=402)
        return EmbeddingProviderError(_OPENAI_RATE_LIMIT_MESSAGE, status_code=429)

    def _map_api_status_error(self, error: APIStatusError) -> EmbeddingProviderError:
        if error.status_code == 429 and self._is_quota_error(error):
            return EmbeddingProviderError(_OPENAI_QUOTA_MESSAGE, status_code=402)
        if error.status_code == 429:
            return EmbeddingProviderError(_OPENAI_RATE_LIMIT_MESSAGE, status_code=429)
        return EmbeddingProviderError(
            f"OpenAI embedding request failed: {error.message}",
            status_code=error.status_code or 502,
        )

    def _is_quota_error(self, error: RateLimitError | APIStatusError) -> bool:
        body = getattr(error, "body", None)
        if isinstance(body, dict):
            error_body = body.get("error", {})
            if isinstance(error_body, dict):
                if error_body.get("code") == "insufficient_quota":
                    return True
                if error_body.get("type") == "insufficient_quota":
                    return True
        return "insufficient_quota" in str(error).lower()
