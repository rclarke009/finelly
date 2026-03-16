## 3. Request and response models (Pydantic)

# Define Pydantic models for the two main flows. 
# For **ingest:** a request body with at least `text` 
# (required), and optional `doc_id`, `title`, `source`, 
# and chunking options (e.g. `chunk_size`, `chunk_overlap`). 
# Define a response that includes `doc_id`, `num_chunks`, and 
# whatever embedding metadata you plan to return. 
# 
# For **ask:** a request with `question`, optional `top_k` and optional 
# `doc_id` (to restrict search to one document), and a response with 
# `answer` and a list of retrieved chunks (each with something like `chunk_id`, 
# `doc_id`, `score`, and a short `content_snippet`). (made that into RetrievedChunk class)

import uuid
from pydantic import BaseModel, Field, model_validator
from typing import Literal

# --- Financial (Private Cash Assistant) ---

class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1)
    type: str | None = None
    institution: str | None = None
    document_id: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    institution: str | None = None
    document_id: str | None = None


class AccountResponse(BaseModel):
    id: str
    name: str
    type: str | None = None
    institution: str | None = None
    document_id: str | None = None
    created_at: int


class PositionCreate(BaseModel):
    account_id: str = Field(..., min_length=1)
    asset_type: str = Field(..., min_length=1)
    description: str | None = None
    principal: float | None = None
    rate_apr: float | None = None
    maturity_date: str | None = None
    document_id: str | None = None


class PositionUpdate(BaseModel):
    description: str | None = None
    principal: float | None = None
    rate_apr: float | None = None
    maturity_date: str | None = None
    document_id: str | None = None


class PositionResponse(BaseModel):
    id: str
    account_id: str
    asset_type: str
    description: str | None = None
    principal: float | None = None
    rate_apr: float | None = None
    maturity_date: str | None = None
    document_id: str | None = None
    created_at: int
    updated_at: int


class ObligationCreate(BaseModel):
    description: str = Field(..., min_length=1)
    due_date: str = Field(..., min_length=1)
    amount_estimate: float | None = None
    priority: str | None = None
    document_id: str | None = None


class ObligationUpdate(BaseModel):
    description: str | None = None
    due_date: str | None = None
    amount_estimate: float | None = None
    priority: str | None = None
    document_id: str | None = None


class ObligationResponse(BaseModel):
    id: str
    description: str
    due_date: str
    amount_estimate: float | None = None
    priority: str | None = None
    document_id: str | None = None
    created_at: int


class TriggerEventResponse(BaseModel):
    id: str
    trigger_type: str
    entity_type: str
    entity_id: str
    event_date: str | None = None
    evaluated_at: int
    status: str


# Sources used in advice (discriminated: user_data | web)
class UserDataSource(BaseModel):
    type: Literal["user_data"] = "user_data"
    entity_type: str = Field(..., description="account | position | obligation")
    id: str
    label: str = Field(..., description="Human-readable short label")


class WebSource(BaseModel):
    type: Literal["web"] = "web"
    quote: str | None = None
    url: str | None = None
    source_name: str | None = None


AdviceSource = UserDataSource | WebSource


class DecisionResponse(BaseModel):
    status: Literal["no_action_required", "actionable"] = Field(...)
    triggers: list[TriggerEventResponse] = Field(default_factory=list)
    memo: str | None = None
    sources: list[UserDataSource | WebSource] = Field(default_factory=list)
    openai_advice: list[str] = Field(
        default_factory=list,
        description="Sanitized CD advice from OpenAI (one per maturity trigger); empty if not configured or no maturity triggers.",
    )


class DecisionHistoryItem(BaseModel):
    id: str
    evaluated_at: int
    status: str
    memo: str | None = None
    trigger_ids: str | None = None


class RemoteLogEventPayload(BaseModel):
    """Sanitized payload for remote log (no PII). Sent to Supabase Edge Function when REMOTE_LOG_URL is set."""

    timestamp: str
    level: Literal["ERROR", "WARNING", "INFO"]
    message: str
    route: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    duration_ms: int | None = None
    error_type: str | None = None
    stack_trace: str | None = None
    instance_id: str | None = None


# --- Document / RAG (existing) ---

class ChunkingOptions(BaseModel):
    strategy: Literal["chars", "sentences"] = "chars"
    chunk_size: int = Field(default=800, description= "Chunk size")
    chunk_overlap: int = Field(default=100, description="Chunk overlap")

    @model_validator(mode="after")
    def check_chunking_bounds(self)->"ChunkingOptions":
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return self

class IngestRequest (BaseModel):
    text: str = Field(..., min_length=1,description="Text to ingest")
    doc_id: str | None = None
    title: str | None = None
    source: str | None = None
    tags: list[str] | None = Field(default=None, description="Optional tags for grouping (e.g. 2024, Checking)")
    chunking_options: ChunkingOptions | None = None
    confirm_duplicate_content: bool = Field(
        default=False,
        description="If True, allow ingesting the same text/PDF again under a different doc_id (skip duplicate-content warning).",
    )
    account_id: str | None = Field(default=None, description="Link document to this account id")

    @model_validator(mode='after')
    def set_defaults(self) -> "IngestRequest":
        doc_id = self.doc_id if self.doc_id is not None else str(uuid.uuid4())
        chunking_options = self.chunking_options if self.chunking_options is not None else ChunkingOptions()
        return self.model_copy(update={"doc_id":doc_id, "chunking_options":chunking_options})

class IngestResponse(BaseModel):
    doc_id: str = Field(..., description="doc_id")
    num_chunks: int = Field(..., description="Number of chunks")
    embedding_model: str = Field(..., description="Embedding model")
    dim: int = Field(..., description="Embedding vector dimension")


class AskRequest(BaseModel):
    question: str = Field(..., description="Question from user")
    top_k: int = Field(default=5, description="Will pull the top __ matches")
    doc_id: str | None = Field(default=None, description="Search only within this document")
    doc_ids: list[str] | None = Field(default=None, description="Search only within these document ids")
    tag: str | None = Field(default=None, description="Search only within documents with this tag")
    use_rag: bool = True

class RetrievedChunk(BaseModel):
    chunk_id: str = Field(..., description="chunk_id")
    doc_id: str = Field(..., description="doc_id")
    score: float = Field(..., description="score")
    content_snippet: str = Field(..., description="content_snippet")

class AskResponse(BaseModel):
    answer: str = Field(...,description="Answer from system")
    top_chunks: list[RetrievedChunk] = Field(..., description="top _ chunks")
    prompt_tokens_estimate: int | None = Field(default= None, description="prompt tokens estimate") # (stub ok)


# General-path (OpenAI only): templated params, no PII
class AskGeneralRequest(BaseModel):
    template: Literal["cd_advice", "cd_rates_summary"] = Field(
        ...,
        description="Whitelisted template; only server-built prompts are sent to OpenAI.",
    )
    amount: float | None = Field(default=None, description="For cd_advice: principal amount (no identifiers).")
    term_months: int | None = Field(default=None, description="For cd_advice: CD term in months.")


class AskGeneralResponse(BaseModel):
    answer: str = Field(..., description="Answer from OpenAI for the templated question.")


class AskImageResponse(BaseModel):
    answer: str = Field(..., description="Report-style text from LLaVA (vision model) for the image.")


class DocumentSummary(BaseModel):
    doc_id: str = Field(..., description="Document id")
    title: str | None = Field(default=None, description="Title")
    source: str | None = Field(default=None, description="Source")
    created_at: int = Field(..., description="Unix timestamp")
    num_chunks: int = Field(..., description="Number of chunks")
    snippet: str | None = Field(default=None, description="First ~250 chars of first chunk")
    tags: list[str] = Field(default_factory=list, description="Tags for grouping/filtering")
    linked_account_ids: list[str] = Field(default_factory=list, description="Account IDs that reference this document")


class DocumentUpdateRequest(BaseModel):
    """Optional fields for PATCH /documents/{doc_id}. Omit a field to leave it unchanged."""

    tags: list[str] | None = Field(default=None, description="Replace document tags with this list")
    account_id: str | None = Field(default=None, description="Set linked account (null = unlink all)")


class DocumentsListResponse(BaseModel):
    documents: list[DocumentSummary] = Field(..., description="List of ingested documents")


class IngestGoogleDriveRequest(BaseModel):
    """Request to ingest documents from Google Drive (read-only)."""

    folder_id: str | None = Field(default=None, description="Limit to files in this folder")
    file_ids: list[str] | None = Field(default=None, description="If set, only these file IDs (folder_id ignored)")


class IngestGoogleDriveResponse(BaseModel):
    """Result of Google Drive sync."""

    ingested: int = Field(..., description="Number of documents ingested")
    skipped: int = Field(default=0, description="Number skipped (e.g. duplicate doc_id)")
    errors: list[str] = Field(default_factory=list, description="Error messages for failed docs")
    doc_ids: list[str] = Field(default_factory=list, description="doc_ids that were ingested")
