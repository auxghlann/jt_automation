class AuthRequiredError(Exception):
    """Raised when Google authentication is required but interactive mode is off."""
    pass
