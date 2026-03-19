from typing import Any, Optional, List
from app.schemas.response import (
    APIResponse, ResponseStatus, Meta, AuthTokens, RateLimitInfo, 
    ErrorCode, ErrorDetail
)

def success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    meta: Optional[Meta] = None,
    auth: Optional[AuthTokens] = None,
    rate_limit: Optional[RateLimitInfo] = None
) -> dict:
    """Create a success response"""
    response = APIResponse(
        status=ResponseStatus.SUCCESS,
        data=data,
        message=message,
        meta=meta,
        auth=auth,
        rate_limit=rate_limit
    )
    return response.model_dump(mode='json', exclude_none=True)

def error_response(
    message: str,
    errors: Optional[List[dict]] = None,
    error_code: Optional[ErrorCode] = None,
    status_code: int = 400
) -> dict:
    """Create an error response"""
    if errors:
        error_details = [ErrorDetail(**e) for e in errors]
    elif error_code:
        error_details = [ErrorDetail(message=message, code=error_code)]
    else:
        error_details = [ErrorDetail(message=message)]
    
    response = APIResponse(
        status=ResponseStatus.ERROR,
        data=None,
        message=message,
        errors=error_details
    )
    return response.model_dump(mode='json', exclude_none=True)
