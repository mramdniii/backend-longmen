from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class AccountLockedException(AppException):
    def __init__(self, detail: str = "Account is locked"):
        super().__init__(status_code=status.HTTP_423_LOCKED, detail=detail)


class InvalidTokenException(AppException):
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
