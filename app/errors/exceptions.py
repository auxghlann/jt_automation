class AuthRequiredError(Exception):
    """Raised when Google authentication is required but interactive mode is off."""
    pass


def find_auth_error(exc: BaseException) -> bool:
    """Recursively searches a BaseExceptionGroup for AuthRequiredError.

    Needed because LangGraph wraps node exceptions in BaseExceptionGroup,
    so a flat 'except AuthRequiredError' never matches.
    """
    if isinstance(exc, AuthRequiredError):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return any(find_auth_error(sub) for sub in exc.exceptions)
    return False
