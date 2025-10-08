import logging
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from .logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API errors, carrying a message and HTTP-like status code."""

    def __init__(self, message: str, code: int = 500):
        super().__init__(message)
        self.code = code
        self.message = message


# not clear on the purpose of a typevar here?
F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def handle_exceptions(func: F) -> F:
    """Decorator to wrap controller methods with logging and exception handling."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__} with args={args[1:]} kwargs={kwargs}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully.")
            return result
        except APIException as e:
            logger.error(
                f"APIException in {func.__name__}: {e.message} (code={e.code})"
            )
            return {"error": e.message, "code": e.code}
        except Exception as e:
            logger.exception(f"Unhandled exception in {func.__name__}: {e}")
            return {"error": "InternalServerError", "code": 500}

    return wrapper  # type: ignore


class Controller:
    """
    Base controller class with built-in logging, exception management,
    and async business logic execution helper. Inherit and use @handle_exceptions
    on endpoint methods to ensure consistent behavior.
    """

    def __init__(self) -> None:
        self.logger = logger

    # As far as I can tell this isn't actually being used anywhere though maybe I'm missing something.

    async def run_business_logic(
        self, logic: Coroutine[Any, Any, Any], *args, **kwargs
    ) -> Any:
        """
        Execute a business logic coroutine with standardized logging and error handling.
        Returns the result or a structured error dict.
        """
        self.logger.info(f"Running business logic: {logic.__name__}")
        try:
            result = await logic(*args, **kwargs)
            self.logger.info(f"Business logic {logic.__name__} succeeded.")
            return result
        except APIException as e:
            self.logger.error(
                f"APIException in business logic {logic.__name__}: {e.message} (code={e.code})"
            )
            return {"error": e.message, "code": e.code}
        except Exception as e:
            self.logger.exception(
                f"Unhandled exception in business logic {logic.__name__}: {e}"
            )
            return {"error": "InternalServerError", "code": 500}
