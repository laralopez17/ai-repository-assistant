from openai import APIStatusError, OpenAI, RateLimitError

from app.core.config import OPENAI_API_KEY, OPENAI_CHAT_MODEL
from app.core.errors import LLMProviderError, MissingApiKeyError
from app.domain.models import SearchResult
from app.services.rag_prompt import SYSTEM_PROMPT, build_user_prompt

_OPENAI_QUOTA_MESSAGE = (
    "OpenAI quota or billing limit exceeded. "
    "Check your OpenAI account billing settings."
)
_OPENAI_RATE_LIMIT_MESSAGE = (
    "OpenAI rate limit exceeded. Try again later."
)


class OpenAILLMProvider:
    def generate_answer(self, question: str, context_chunks: list[SearchResult]) -> str:
        if not OPENAI_API_KEY:
            raise MissingApiKeyError("OPENAI_API_KEY is not configured")

        client = OpenAI(api_key=OPENAI_API_KEY)
        try:
            response = client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(question, context_chunks),
                    },
                ],
            )
        except RateLimitError as error:
            raise self._map_rate_limit_error(error) from error
        except APIStatusError as error:
            raise self._map_api_status_error(error) from error

        message_content = response.choices[0].message.content
        if not message_content:
            raise LLMProviderError(
                "OpenAI chat completion returned an empty response.",
                status_code=502,
            )
        return message_content

    def _map_rate_limit_error(self, error: RateLimitError) -> LLMProviderError:
        if self._is_quota_error(error):
            return LLMProviderError(_OPENAI_QUOTA_MESSAGE, status_code=402)
        return LLMProviderError(_OPENAI_RATE_LIMIT_MESSAGE, status_code=429)

    def _map_api_status_error(self, error: APIStatusError) -> LLMProviderError:
        if error.status_code == 429 and self._is_quota_error(error):
            return LLMProviderError(_OPENAI_QUOTA_MESSAGE, status_code=402)
        if error.status_code == 429:
            return LLMProviderError(_OPENAI_RATE_LIMIT_MESSAGE, status_code=429)
        return LLMProviderError(
            f"OpenAI chat request failed: {error.message}",
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
