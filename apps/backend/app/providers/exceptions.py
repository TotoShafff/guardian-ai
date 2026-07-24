"""Exceptions raised by `AIProvider` adapters.

A provider-agnostic exception hierarchy so concrete adapters (e.g.
`OpenRouterProvider`) never leak vendor/transport-specific exception types
(`httpx.*`, a vendor SDK's own errors, ...) to the orchestrator — callers
only ever need to catch these.
"""


class AIProviderError(Exception):
    """Base class for every error raised by an `AIProvider` adapter."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when a provider is misconfigured (e.g. a missing API key)."""


class AIProviderRequestError(AIProviderError):
    """Raised when sending a request to the provider fails.

    Covers network errors, timeouts, and non-2xx HTTP responses.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        #: The HTTP status code, when the error was caused by a non-2xx
        #: response; `None` for network/timeout errors that never received one.
        self.status_code = status_code


class AIProviderResponseError(AIProviderError):
    """Raised when a provider's response cannot be parsed into expected content."""
