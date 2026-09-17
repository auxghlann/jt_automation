class AuthRequiredError(Exception):
    """Raised when Google authentication is required but interactive mode is off."""
    pass


def unwrap_exception_group(exc: BaseException) -> list[BaseException]:
    """Recursively extracts all non-group leaf exceptions from a BaseExceptionGroup."""
    if isinstance(exc, BaseExceptionGroup):
        leafs = []
        for sub in exc.exceptions:
            leafs.extend(unwrap_exception_group(sub))
        return leafs
    return [exc]


def format_exception_details(exc: BaseException) -> list[str]:
    """Returns human-readable descriptions for all leaf exceptions in a group or single exception."""
    leafs = unwrap_exception_group(exc)
    details = []
    for leaf in leafs:
        msg = str(leaf).strip()
        type_name = type(leaf).__name__
        if msg:
            details.append(f"[{type_name}] {msg}")
        else:
            details.append(f"[{type_name}]")
    return details


def find_auth_error(exc: BaseException) -> bool:
    """Recursively searches an exception or BaseExceptionGroup for AuthRequiredError."""
    return any(isinstance(leaf, AuthRequiredError) for leaf in unwrap_exception_group(exc))
