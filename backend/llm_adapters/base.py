import abc
from typing import Any, Dict, Optional

DEFAULT_CODE_SYSTEM_PROMPT = (
    "You are a senior data scientist. Always respond with a compact JSON object containing "
    "'reasoning' (short description of the chosen approach), 'code' (complete Python script "
    "with real newline characters), and optional 'warnings' (array of caveats). Do not wrap "
    "the JSON in Markdown fences or add extra text."
)

DEFAULT_CODE_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the statistical approach and key checks performed.",
        },
        "code": {
            "type": "string",
            "description": "Executable Python code ready to run in the analysis sandbox.",
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of caveats, assumption violations, or follow-up suggestions.",
        },
    },
    "required": ["code"],
    "additionalProperties": False,
}



class LLMAdapter(abc.ABC):
    """Base class for LLM provider adapters."""

    name: str

    def __init__(self, *, api_key: Optional[str], default_models: Optional[list[str]] = None):
        self.api_key = api_key
        self.default_models = default_models or []

    @abc.abstractmethod
    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code from the provided prompt."""

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Exchange conversational messages with the LLM.

        Adapters can override this method; by default it raises NotImplementedError.
        """

        raise NotImplementedError(f"{self.name} adapter does not support chat yet.")

    async def ensure_credentials(self) -> None:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured.")

    async def list_models(self) -> list[str]:
        """Return list of models supported by this adapter."""
        return self.default_models
