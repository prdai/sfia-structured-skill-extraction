# TODO: explore adding the raw crawled pages (crawler R2 output) as a third
# retrieval source, instead of only the processed skill-level records.
import json

from crewai.tools import BaseTool
from embedding_matcher.matcher import EmbeddingMatcher
from keyword_matcher.matcher import KeywordMatcher
from pydantic import BaseModel, ConfigDict, Field

from . import CORPUS_PATH


class SearchInput(BaseModel):
    query: str = Field(description="Free-text query describing a job, course, role, or skill")


class SemanticSearchTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "semantic_skill_search"
    description: str = (
        "Semantic (embedding) search over SFIA skill-level descriptions. "
        "Finds skills whose descriptions are similar in meaning to the query, "
        "even without shared words. Returns JSON matches with skill, level and score."
    )
    args_schema: type[BaseModel] = SearchInput
    matcher: EmbeddingMatcher = Field(default_factory=EmbeddingMatcher)

    def _run(self, query: str) -> str:
        matches = self.matcher.search(query)
        return json.dumps([m.model_dump(exclude={"source_url"}) for m in matches[:10]], indent=2)


class KeywordSearchTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "keyword_skill_search"
    description: str = (
        "Keyword (BM25) search over SFIA skill-level descriptions. "
        "Finds skills whose descriptions share exact terms with the query; "
        "good for jargon, acronyms and named technologies. "
        "Returns JSON matches with skill, level and score."
    )
    args_schema: type[BaseModel] = SearchInput
    matcher: KeywordMatcher = Field(default_factory=lambda: KeywordMatcher.from_corpus(CORPUS_PATH))

    def _run(self, query: str) -> str:
        matches = self.matcher.search(query)
        return json.dumps([m.model_dump(exclude={"source_url"}) for m in matches[:10]], indent=2)
