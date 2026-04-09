"""Custom OAuth2 validator to assign user to client credentials tokens."""

from oauth2_provider.oauth2_validators import OAuth2Validator


class CustomOAuth2Validator(OAuth2Validator):
    """Assign the application's user to client credentials tokens.

    DOT 3.x creates client credentials tokens with user=None by default,
    which breaks DRF's IsAuthenticated permission check.
    """

    def _create_access_token(self, expires, request, token, source_refresh_token=None):
        if request.grant_type == "client_credentials" and request.user is None:
            request.user = request.client.user
        return super()._create_access_token(
            expires, request, token, source_refresh_token
        )
