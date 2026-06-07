from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from personal_intelligence.auth.oauth import (
    create_auth_code,
    exchange_code,
    refresh_access_token,
    register_client,
)

router = APIRouter()


@router.get("/.well-known/oauth-protected-resource")
async def get_well_known():
    return {
        "resource": "https://adel-intelligence.com",
        "authorization_servers": ["https://adel-intelligence.com"],
    }


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    return {
        "issuer": "https://adel-intelligence.com",
        "authorization_endpoint": "https://adel-intelligence.com/api/oauth/authorize",
        "token_endpoint": "https://adel-intelligence.com/api/oauth/token",
        "registration_endpoint": "https://adel-intelligence.com/api/oauth/register",
        "code_challenge_methods_supported": ["S256"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
    }


@router.post("/api/oauth/register")
async def register(request: Request):
    body = await request.json()
    result = register_client(
        client_name=body.get("client_name", "unknown"),
        redirect_uris=body.get("redirect_uris", []),
    )
    return {
        "client_id": result["client_id"],
        "client_secret": result["client_secret"],
        "client_name": body.get("client_name", "unknown"),
        "redirect_uris": body.get("redirect_uris", []),
        "grant_types": body.get("grant_types", ["authorization_code", "refresh_token"]),
        "response_types": body.get("response_types", ["code"]),
        "token_endpoint_auth_method": body.get("token_endpoint_auth_method", "none"),
    }


@router.get("/api/oauth/authorize")
async def authorize(
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    state: str = "",
):
    code = create_auth_code(
        client_id=client_id,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
    )
    return RedirectResponse(url=f"{redirect_uri}?code={code}&state={state}")


@router.post("/api/oauth/token")
async def token(
    grant_type: str = Form(),
    code: str = Form(""),
    code_verifier: str = Form(""),
    client_id: str = Form(""),
    client_secret: str = Form(""),
    refresh_token: str = Form(""),
):
    if grant_type == "authorization_code":
        result = exchange_code(
            code=code, code_verifier=code_verifier, client_id=client_id
        )
    elif grant_type == "refresh_token":
        result = refresh_access_token(refresh_token=refresh_token, client_id=client_id)
    else:
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    if not result:
        raise HTTPException(status_code=400, detail="invalid_grant")

    return result
