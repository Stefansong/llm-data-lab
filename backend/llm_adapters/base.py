import abc
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Timeout configuration (in seconds)
DEFAULT_CODE_GENERATION_TIMEOUT = 40.0
DEFAULT_CHAT_TIMEOUT = 50.0
DEFAULT_MODEL_LIST_TIMEOUT = 20.0

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
    """Base class for LLM provider adapters.

    All adapters must implement the generate_code method, and optionally override
    the chat and list_models methods to provide full functionality.

    Attributes:
        name: Identifier for this adapter (e.g., "openai", "anthropic")
        api_key: API key for authentication
        default_models: List of fallback model names if dynamic fetching fails
    """

    name: str

    def __init__(self, *, api_key: Optional[str], default_models: Optional[list[str]] = None):
        """Initialize the adapter with credentials and default models.

        Args:
            api_key: API key for the LLM provider
            default_models: List of model names to use as fallback
        """
        self.api_key = api_key
        self.default_models = default_models or []
        logger.debug(f"Initialized {self.name} adapter with {len(self.default_models)} default models")

    @abc.abstractmethod
    async def generate_code(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate code from the provided prompt.

        Args:
            prompt: The user's task description
            **kwargs: Additional parameters (model, temperature, etc.)

        Returns:
            Dict containing:
                - raw: Original API response
                - code: Generated code string
                - usage: Token usage statistics

        Raises:
            RuntimeError: If API key is not configured
            HTTPException: If API request fails
        """

    async def chat(self, messages: list[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Exchange conversational messages with the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, response_format, etc.)

        Returns:
            Dict containing:
                - raw: Original API response
                - message: The assistant's message dict
                - usage: Token usage statistics

        Raises:
            NotImplementedError: If chat is not supported by this adapter
        """
        raise NotImplementedError(f"{self.name} adapter does not support chat yet.")

    async def ensure_credentials(self) -> None:
        """Verify that API credentials are configured.

        Raises:
            RuntimeError: If API key is missing
        """
        if not self.api_key:
            logger.error(f"{self.name} API key is not configured")
            raise RuntimeError(f"{self.name} API key is not configured.")

    async def list_models(self) -> list[str]:
        """Return list of models supported by this adapter.

        Returns:
            List of model identifier strings
        """
        return self.default_models
