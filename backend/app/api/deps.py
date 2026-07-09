from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import secure_compare
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]

bearer_scheme = HTTPBearer(auto_error=False)


def _require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    expected_token: str,
    realm: str,
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": f"{realm} bearer token is required."},
        )
    if not secure_compare(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": f"Invalid {realm} token."},
        )


def require_vapi_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    _require_bearer_token(credentials, settings.vapi_tool_secret, "Vapi")


def require_admin_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    _require_bearer_token(credentials, settings.admin_api_token, "admin")


def request_id_header(x_request_id: Annotated[str | None, Header()] = None) -> str | None:
    return x_request_id

