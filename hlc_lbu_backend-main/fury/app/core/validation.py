"""Validation utilities for agent responses.

This module contains reusable validation classes and exceptions
for validating agent responses in pipeline workflows.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, List


@dataclass
class ValidationResult:
    """Result of agent response validation.
    
    Attributes:
        is_valid: Whether the validation passed
        errors: List of error messages (empty if valid)
        warnings: List of warning messages (non-blocking issues)
        data: Optional transformed data to use instead of raw response
        error_code: Optional code for categorizing errors (e.g. "MISSING_FIELD")
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Any = None  # Optional transformed data
    error_code: str = None  # Optional error code for categorization


class AgentValidationError(Exception):
    """Exception raised when agent response validation fails.
    
    Attributes:
        errors: List of validation errors
        step: The pipeline step/agent name where validation failed
    """
    def __init__(self, message: str, errors: List[str], step: str, code: str):
        super().__init__(message, errors, step, code)
        self.errors = errors
        self.step = step
        self.code = code

    def to_dict(self) -> dict:
        return {
            "message": self.args[0] if self.args else self.message,
            "errors": self.errors,
            "step": self.step,
            "code": self.code,
        }
    
    def __reduce__(self):
        # Custom reduce method to ensure all attributes are preserved during pickling
        return (self.__class__, (self.args[0] if self.args else "", self.errors, self.step, self.code))


# Type alias for validator functions
AgentValidator = Callable[[str], ValidationResult]