from app.domain.models import RAGAnswerResult, SearchResult, SourceCitation
from app.services.fake_llm_provider import INSUFFICIENT_CONTEXT_ANSWER
from app.services.llm_provider import LLMProvider
from app.services.semantic_search_service import SemanticSearchService


class RAGAnswerService:
    def __init__(
        self,
        semantic_search_service: SemanticSearchService,
        llm_provider: LLMProvider,
    ) -> None:
        self._semantic_search_service = semantic_search_service
        self._llm_provider = llm_provider

    def answer(
        self,
        index_id: str,
        question: str,
        top_k: int,
        include_tests: bool = True,
    ) -> RAGAnswerResult:
        search_results = self._semantic_search_service.search(
            index_id,
            question,
            top_k,
            include_tests,
        )

        if not search_results:
            return RAGAnswerResult(
                index_id=index_id,
                question=question,
                answer=INSUFFICIENT_CONTEXT_ANSWER,
                sources=[],
            )

        answer = self._llm_provider.generate_answer(question, search_results)
        return RAGAnswerResult(
            index_id=index_id,
            question=question,
            answer=answer,
            sources=[self._to_source(result) for result in search_results],
        )

    def _to_source(self, result: SearchResult) -> SourceCitation:
        return SourceCitation(
            chunk_id=result.chunk_id,
            file_path=result.file_path,
            start_line=result.start_line,
            end_line=result.end_line,
            score=result.score,
            source_type=result.source_type,
        )
