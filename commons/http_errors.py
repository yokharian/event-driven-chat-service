from http import HTTPStatus

from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    InternalServerError,
    NotFoundError,
    ServiceError,
    UnauthorizedError,
)
from aws_lambda_powertools.event_handler.openapi.exceptions import (
    RequestValidationError,
)


class UnauthorizedHTTPError(UnauthorizedError):
    pass


class InternalServerHTTPError(InternalServerError):
    pass


class BadRequestHTTPError(BadRequestError):
    pass


class NotFoundHTTPError(NotFoundError):
    pass


class ForbiddenHTTPError(ServiceError):
    def __init__(self, msg: str = "Forbidden"):
        super().__init__(status_code=HTTPStatus.FORBIDDEN, msg=msg)


class ValidationHTTPError(RequestValidationError):
    def __init__(self, msg: str) -> None:
        super().__init__(errors={"message": msg})
