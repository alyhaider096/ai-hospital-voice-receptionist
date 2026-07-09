class ServiceError(Exception):
    status_code = 400
    code = "service_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    status_code = 404
    code = "not_found"


class SlotUnavailableError(ServiceError):
    status_code = 409
    code = "slot_unavailable"


class ValidationServiceError(ServiceError):
    status_code = 422
    code = "validation_error"

