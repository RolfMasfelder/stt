"""Custom OAuth2 validator to assign user to client credentials tokens."""

from oauth2_provider.oauth2_validators import OAuth2Validator


class CustomOAuth2Validator(OAuth2Validator):
    """Assign the application's user to client credentials tokens.

    DOT 3.x sets request.user = None for client_credentials in
    _save_bearer_token before creating the AccessToken. We override
    that method to restore the application's user afterwards.
    """

    def _save_bearer_token(self, token, request, *args, **kwargs):
        super()._save_bearer_token(token, request, *args, **kwargs)
        if request.grant_type == "client_credentials" and request.client.user:
            from oauth2_provider.models import AccessToken

            AccessToken.objects.filter(
                token=token["access_token"],
                user__isnull=True,
            ).update(user=request.client.user)
