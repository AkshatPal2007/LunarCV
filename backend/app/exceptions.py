"""Custom exceptions for LunarCV API."""


class LunarCVException(Exception):
    """Base exception with user_message for API responses."""

    def __init__(self, message: str, user_message: str = None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message


class ImageLoadError(LunarCVException):
    """Image cannot be loaded or format unsupported."""

    pass


class MatchingError(LunarCVException):
    """Feature matching failed."""

    pass


class RegistrationError(LunarCVException):
    """Registration computation failed."""

    pass
