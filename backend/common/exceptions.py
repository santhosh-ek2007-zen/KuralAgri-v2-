"""
Custom exception handler for KuralAgri REST APIs.
Produces the uniform error envelope specified in SIH_MVP_TECHNICAL_SPECIFICATION.md:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... }
  }
}
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


class KuralAgriException(APIException):
    """Base application exception with explicit code and status."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'BAD_REQUEST'
    default_detail = 'An error occurred.'

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.default_code = code
        super().__init__(detail=detail, code=code)


class BusinessRuleViolation(KuralAgriException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = 'BUSINESS_RULE_VIOLATION'


class ResourceNotFound(KuralAgriException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'NOT_FOUND'


class InsufficientFunds(KuralAgriException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'INSUFFICIENT_FUNDS'


def custom_exception_handler(exc, context):
    """
    Transform DRF exceptions into uniform JSON format:
    {"error": {"code": "...", "message": "...", "details": ...}}
    """
    response = exception_handler(exc, context)

    if response is not None:
        code = getattr(exc, 'default_code', 'API_ERROR')
        if hasattr(exc, 'get_codes'):
            err_codes = exc.get_codes()
            if isinstance(err_codes, str):
                code = err_codes.upper()
            elif isinstance(err_codes, dict):
                code = 'VALIDATION_ERROR'

        message = str(exc.detail) if hasattr(exc, 'detail') and isinstance(exc.detail, str) else 'Request failed'
        details = response.data

        # If details has detail string, promote to message
        if isinstance(details, dict) and 'detail' in details:
            message = str(details.pop('detail'))
            if not details:
                details = None

        response.data = {
            "error": {
                "code": code.upper() if isinstance(code, str) else "VALIDATION_ERROR",
                "message": message,
                "details": details
            }
        }

    return response
