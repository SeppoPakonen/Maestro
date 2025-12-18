class TUError(Exception):
    """Base exception for TU/AST operations."""


class ParserUnavailableError(TUError):
    """Raised when a parser is not available due to missing dependencies."""


class ParserExecutionError(TUError):
    """Raised when a parser encounters an error during execution."""
