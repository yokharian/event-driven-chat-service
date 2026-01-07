from typing import Any, Dict, List, Optional


def success_response(
    data: Any, message: str = "Request successful", status: int = 200
) -> Dict[str, Any]:
    return {"status": status, "message": message, "data": data}


def paginated_response(
    data: List[Any],
    current_page: int,
    page_size: int,
    total_items: int,
    message: str = "Request successful",
    status: int = 200,
) -> Dict[str, Any]:
    total_pages = (total_items + page_size - 1) // page_size
    return {
        "status": status,
        "message": message,
        "data": data,
        "pagination": {
            "currentPage": current_page,
            "pageSize": page_size,
            "totalItems": total_items,
            "totalPages": total_pages,
        },
    }


def error_response(
    message: str,
    code: Optional[str] = None,
    details: Optional[str] = None,
    status: int = 400,
) -> Dict[str, Any]:
    error_object = {"code": code, "message": message, "details": details}
    error_object = {k: v for k, v in error_object.items() if v is not None}  # Remove None values
    return {"status": status, "error": error_object}


def validation_error_response(
    message: str,
    errors: List[Dict[str, str]],
    code: str = "VALIDATION_FAILED",
    status: int = 422,
) -> Dict[str, Any]:
    return {
        "status": status,
        "error": {
            "code": code,
            "message": message,
            "details": "Multiple validation errors occurred.",
        },
        "errors": errors,
    }
