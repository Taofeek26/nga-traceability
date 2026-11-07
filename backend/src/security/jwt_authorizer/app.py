"""REQUEST-type Lambda authorizer for the HTTP API.

Verifies the Authorization: Bearer JWT and, on success, returns an
isAuthorized flag plus the decoded claims as context - every downstream
domain Lambda reads lba_id/role/user_id from that context (http_util.claims)
instead of re-deriving identity itself.
"""
import auth_util


def lambda_handler(event, context):
    header = event.get("headers", {}) or {}
    auth_header = header.get("authorization") or header.get("Authorization") or ""
    token = auth_header[7:] if auth_header.lower().startswith("bearer ") else ""

    data = auth_util.read_session_token(token) if token else None
    if data is None:
        return {"isAuthorized": False}

    return {
        "isAuthorized": True,
        "context": {
            "user_id": str(data["user_id"]),
            "lba_id": str(data["lba_id"]),
            "org_name": data.get("org_name") or "",
            "user_name": data.get("user_name") or "",
            "role": data.get("role") or "",
        },
    }
