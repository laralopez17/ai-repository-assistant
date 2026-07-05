from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.core.errors import EmbeddingProviderError
from app.services.openai_embedding_provider import OpenAIEmbeddingProvider


def _quota_rate_limit_error() -> RateLimitError:
    response = MagicMock()
    response.status_code = 429
    return RateLimitError(
        message="Error code: 429 - insufficient_quota",
        response=response,
        body={"error": {"code": "insufficient_quota", "message": "You exceeded your quota."}},
    )


def _rate_limit_error() -> RateLimitError:
    response = MagicMock()
    response.status_code = 429
    return RateLimitError(
        message="Error code: 429 - rate_limit_exceeded",
        response=response,
        body={"error": {"code": "rate_limit_exceeded", "message": "Rate limit reached."}},
    )


@patch("app.services.openai_embedding_provider.OPENAI_API_KEY", "test-key")
@patch("app.services.openai_embedding_provider.OpenAI")
def test_openai_provider_maps_quota_error(mock_openai_class):
    mock_openai_class.return_value.embeddings.create.side_effect = _quota_rate_limit_error()
    provider = OpenAIEmbeddingProvider()

    with pytest.raises(EmbeddingProviderError) as error_info:
        provider.embed_texts(["hello"])

    assert error_info.value.status_code == 402
    assert "quota or billing" in error_info.value.message.lower()


@patch("app.services.openai_embedding_provider.OPENAI_API_KEY", "test-key")
@patch("app.services.openai_embedding_provider.OpenAI")
def test_openai_provider_maps_rate_limit_error(mock_openai_class):
    mock_openai_class.return_value.embeddings.create.side_effect = _rate_limit_error()
    provider = OpenAIEmbeddingProvider()

    with pytest.raises(EmbeddingProviderError) as error_info:
        provider.embed_texts(["hello"])

    assert error_info.value.status_code == 429
    assert "rate limit" in error_info.value.message.lower()
