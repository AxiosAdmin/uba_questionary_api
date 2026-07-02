"""Route constraints for JWT middleware authentication bypass."""

BYPASS_ROUTES = {
    "/openapi.json",
    "/docs",
    "/redoc",
    "/login",
    "/login/admin",
    "/healthy",
    "/institutions",
    "/stripe/generate",
    "/stripe/webhook/payment",
}
BYPASS_ROUTE_METHODS = {
    ("POST", "/users"),
    ("POST", "/forgot-password"),
    ("POST", "/forgot-nickname"),
    ("POST", "/reset-password"),
    ("POST", "/recover-nickname"),
}


def should_bypass_auth(method: str, path: str) -> bool:
    """Return whether the route should skip JWT validation."""
    return path in BYPASS_ROUTES or (method.upper(), path) in BYPASS_ROUTE_METHODS
