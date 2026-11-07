"""Plain helpers for reading an API Gateway HTTP API (v2) proxy event and
writing a proxy response - no web framework. Every Lambda handler in this
backend uses only these, event['rawPath'], and
event['requestContext']['http']['method'].
"""
import datetime
import decimal
import json
import os

CORS_HEADERS = {
    "Access-Control-Allow-Origin": os.environ.get("FRONTEND_ORIGIN", "*"),
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
}


def method(event):
    return event["requestContext"]["http"]["method"]


def path_params(event):
    return event.get("pathParameters") or {}


def query_params(event):
    return event.get("queryStringParameters") or {}


def json_body(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode()
    try:
        return json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        return {}


def claims(event):
    """Context the JWT authorizer attached - see jwt_authorizer/app.py."""
    return event.get("requestContext", {}).get("authorizer", {}).get("lambda", {}) or {}


def _json_default(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    raise TypeError(f"Not JSON serializable: {value!r}")


def response(status, body=None, headers=None):
    out_headers = dict(CORS_HEADERS)
    if headers:
        out_headers.update(headers)
    out_headers.setdefault("Content-Type", "application/json")
    return {
        "statusCode": status,
        "headers": out_headers,
        "body": json.dumps(body, default=_json_default) if body is not None else "",
    }


def ok(body):
    return response(200, body)


def created(body):
    return response(201, body)


def error(status, message):
    return response(status, {"error": message})


def forbidden(message="You don't have permission to do that."):
    return error(403, message)


def require_role(event, allowed_roles):
    """Returns a forbidden() response if the caller's role isn't allowed,
    else None. Always re-checks server-side - the JWT authorizer only
    proves *who* the caller is, never *what* they're allowed to do."""
    role = claims(event).get("role")
    if role not in allowed_roles:
        return forbidden()
    return None
