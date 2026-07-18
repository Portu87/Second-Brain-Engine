"""Domain-specific errors."""


class SecondBrainError(Exception):
    """Base exception for expected engine failures."""


class ProjectError(SecondBrainError):
    """Raised when a project cannot be read or changed safely."""


class CompilationError(SecondBrainError):
    """Raised when approved decisions cannot be compiled deterministically."""
