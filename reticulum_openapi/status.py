"""Enumeration of common HTTP-like status codes used by the framework."""

from enum import IntEnum

# pretty sure this enumeration is defined in many other frameworks and libraries
# but more importantly, I don't know why we'd choose to use http error codes
# apart from trying to accomadate for restrictions of the openapi spec as the
# generation source.



class StatusCode(IntEnum):
    """Common HTTP-like status codes used by the framework."""

    # Success 2xx
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # Client error 4xx
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409

    # Server error 5xx
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503
