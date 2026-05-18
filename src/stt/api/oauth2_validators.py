"""Custom OAuth2 validator to assign user to client credentials tokens."""

import logging

from oauth2_provider.oauth2_validators import OAuth2Validator


logger = logging.getLogger(__name__)


class CustomOAuth2Validator(OAuth2Validator):
    """Assign the application's user to client credentials tokens.

    DOT 3.x sets request.user = None for client_credentials in
    _save_bearer_token before creating the AccessToken. We override
    that method to restore the application's user afterwards.
    """

    def _save_bearer_token(self, token, request, *args, **kwargs):
        logger.warning(
            "CustomOAuth2Validator._save_bearer_token called, grant_type=%s",
            request.grant_type,
        )
        super()._save_bearer_token(token, request, *args, **kwargs)
        if request.grant_type == "client_credentials" and request.client.user:
            from oauth2_provider.models import AccessToken

            updated = updated = AccessToken.objects.filter(
                token=token["access_token"],
                user__isnull=True,
            ).update(user=request.client.user)
            logger.warning(
                "CustomOAuth2Validator: updated %d tokens for user %s",
                updated,
                request.client.user,
            )
