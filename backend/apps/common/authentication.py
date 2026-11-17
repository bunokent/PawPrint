"""Session authentication that answers 401 (not 403) so the axios client can detect expiry."""

from rest_framework.authentication import SessionAuthentication


class SessionAuthenticationWith401(SessionAuthentication):
    def authenticate_header(self, request) -> str:
        return "Session"
