"""Custom exceptions for LunarCV API."""


class LunarCVError(Exception):
    """Base exception with user_message for API responses."""

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message


class ImageLoadError(LunarCVError):
    """Image cannot be loaded or format unsupported."""

    pass


class MatchingError(LunarCVError):
    """Feature matching failed."""

    pass


class RegistrationError(LunarCVError):
    """Registration computation failed."""

    pass
