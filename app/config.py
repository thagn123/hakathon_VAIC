import os
import warnings
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

_VALID_RAG_PROVIDERS = ("local", "mcp", "hybrid")


def _resolve_rag_provider() -> str:
    """RAG_PROVIDER (local|mcp|hybrid) is the source of truth.

    RAG_MCP_ENABLED is kept only for backward compatibility: if RAG_PROVIDER
    is not explicitly set but RAG_MCP_ENABLED is, map true->hybrid (the old
    code's "try MCP, silently fall through to local on any exception"
    behaviour) and false->local, and print a one-time deprecation warning.
    Default with neither set is "local" -- a safe default when no MCP server
    has been deployed (see docs/RAG_PROVIDER_AND_FALLBACK.md).
    """
    explicit = os.getenv("RAG_PROVIDER")
    if explicit is not None:
        value = explicit.strip().lower()
        if value not in _VALID_RAG_PROVIDERS:
            raise ValueError(
                f"Invalid RAG_PROVIDER={explicit!r}; must be one of {_VALID_RAG_PROVIDERS}"
            )
        return value
    legacy = os.getenv("RAG_MCP_ENABLED")
    if legacy is not None:
        mapped = "hybrid" if legacy.strip().lower() == "true" else "local"
        warnings.warn(
            "RAG_MCP_ENABLED is deprecated; set RAG_PROVIDER=local|mcp|hybrid instead. "
            f"Mapping RAG_MCP_ENABLED={legacy!r} -> RAG_PROVIDER={mapped!r} for this run.",
            DeprecationWarning,
            stacklevel=2,
        )
        return mapped
    return "local"


class Settings(BaseModel):
    # API Keys (Sẽ đọc từ Environment Variables)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Model Configurations
    # Default LLM + embedding route through Google AI Studio (the GOOGLE_API_KEY
    # is the AI Studio key). gemma-4-31b-it is the chat model; gemini-embedding-2
    # is the embedding model (see app/knowledge/index.py / services/rag_mcp).
    DEFAULT_LLM: str = os.getenv("DEFAULT_LLM", "google")  # google | openai | ollama
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemma-4-31b-it")
    GOOGLE_ENDPOINT: str = os.getenv(
        "GOOGLE_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    INTENT_USE_LLM: bool = os.getenv("INTENT_USE_LLM", "false").lower() == "true"
    # Expert LLM enrichment is opt-in. The deterministic expert services and
    # collaboration contracts still run when disabled/provider-down.
    AGENTIC_LLM_ENABLED: bool = os.getenv("AGENTIC_LLM_ENABLED", "false").lower() == "true"
    MODEL_TIMEOUT_SECONDS: float = float(os.getenv("MODEL_TIMEOUT_SECONDS", "15"))
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", "10485760"))
    
    # OCR fallback (app/knowledge/ocr.py) for scanned/image PDFs where
    # pypdf's text-layer extraction yields no usable text. Local Tesseract
    # only -- never sends document bytes to an external service. Language
    # data lives in-repo (data/ocr_tessdata) rather than relying on the
    # system Tesseract install's tessdata, which may not include Vietnamese.
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_LANG: str = os.getenv("OCR_LANG", "vie+eng")
    OCR_MIN_CONFIDENCE: float = float(os.getenv("OCR_MIN_CONFIDENCE", "0.35"))
    OCR_DPI: int = int(os.getenv("OCR_DPI", "300"))
    TESSDATA_DIR: str = os.getenv("TESSDATA_DIR", "./data/ocr_tessdata")
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

    # Vector DB settings
    VECTOR_DB_DIR: str = os.getenv("VECTOR_DB_DIR", "./data/vector_db")
    V2_DB_PATH: str = os.getenv("V2_DB_PATH", "./data/state/v2.sqlite3")
    AUDIT_LOG_PATH: str = os.getenv("AUDIT_LOG_PATH", "./data/logs/audit.jsonl")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEMO_AUTH_ENABLED: bool = os.getenv(
        "DEMO_AUTH_ENABLED", "true" if os.getenv("APP_ENV", "development") == "development" else "false"
    ).lower() == "true"
    # Local-only login boundary. Replace with enterprise SSO in pilot/production.
    DEMO_LOGIN_PASSWORD: str = os.getenv("DEMO_LOGIN_PASSWORD", "demo1234")
    AUTH_SECRET: str = os.getenv("AUTH_SECRET", os.getenv("APPROVAL_SECRET", "demo-only-change-me"))
    AUTH_TOKEN_TTL_SECONDS: int = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(8 * 60 * 60)))

    # Enterprise data backend. Empty => local SQLite mirrors (data/mock_database).
    # Set DATABASE_URL to a postgresql:// DSN to use the PostgreSQL
    # enterprise adapters (app/integrations/pg.py) for CRM/IAM/SSO.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # App Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    APPROVAL_SECRET: str = os.getenv("APPROVAL_SECRET", "demo-only-change-me")
    APPROVAL_TOKEN_TTL_SECONDS: int = int(os.getenv("APPROVAL_TOKEN_TTL_SECONDS", 300))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # RAG MCP Server Integration
    # RAG_MCP_ENABLED is deprecated (kept only so old .env files don't break
    # imports); RAG_PROVIDER is what app/knowledge/{service,legal_service}.py
    # actually read. See _resolve_rag_provider() above.
    RAG_MCP_ENABLED: bool = os.getenv("RAG_MCP_ENABLED", "true").lower() == "true"
    RAG_PROVIDER: str = _resolve_rag_provider()
    RAG_MCP_FAILURE_THRESHOLD: int = int(os.getenv("RAG_MCP_FAILURE_THRESHOLD", "3"))
    RAG_MCP_COOLDOWN_SECONDS: float = float(os.getenv("RAG_MCP_COOLDOWN_SECONDS", "30"))
    RAG_MCP_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("RAG_MCP_REQUEST_TIMEOUT_SECONDS", "3"))
    RAG_MCP_HALF_OPEN_MAX_CALLS: int = int(os.getenv("RAG_MCP_HALF_OPEN_MAX_CALLS", "1"))
    RAG_MCP_WARNING_COOLDOWN_SECONDS: float = float(os.getenv("RAG_MCP_WARNING_COOLDOWN_SECONDS", "30"))
    RAG_MCP_PRODUCT_URL: str = os.getenv("RAG_MCP_PRODUCT_URL", "http://localhost:8100/mcp/product")
    RAG_MCP_PRODUCT_TOKEN: str = os.getenv("RAG_MCP_PRODUCT_TOKEN", "local-rag-mcp-change-me-product")
    RAG_MCP_LEGAL_URL: str = os.getenv("RAG_MCP_LEGAL_URL", "http://localhost:8100/mcp/legal")
    RAG_MCP_LEGAL_TOKEN: str = os.getenv("RAG_MCP_LEGAL_TOKEN", "local-rag-mcp-change-me-legal")
    RAG_MCP_CREDIT_URL: str = os.getenv("RAG_MCP_CREDIT_URL", "http://localhost:8100/mcp/credit")
    RAG_MCP_CREDIT_TOKEN: str = os.getenv("RAG_MCP_CREDIT_TOKEN", "local-rag-mcp-change-me-credit")

settings = Settings()
