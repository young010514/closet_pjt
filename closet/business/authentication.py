from rest_framework.authentication import SessionAuthentication


class SessionAuthentication401(SessionAuthentication):
    """SessionAuthentication that returns 401 for unauthenticated requests.

    Standard SessionAuthentication returns None from authenticate_header(),
    which causes DRF to coerce 401 responses to 403. This subclass provides
    a WWW-Authenticate header so that unauthenticated requests receive a
    proper 401 Unauthorized response.
    """

    def authenticate_header(self, request):
        return 'Session'
