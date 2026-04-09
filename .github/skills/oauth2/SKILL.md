---
name: oauth2
display_name: OAuth2 & django-oauth-toolkit
version: 1.0.0
author: Rolf Masfelder
description: "Use when: modifying OAuth2 configuration, django-oauth-toolkit (DOT) settings, CustomOAuth2Validator, client_credentials flow, token permissions, or debugging 403/401 errors related to OAuth2 tokens"
---

# OAuth2 & django-oauth-toolkit (DOT)

Use this skill when working on OAuth2 authentication/authorization, modifying `OAUTH2_PROVIDER` settings, the `CustomOAuth2Validator`, or debugging token-related permission issues.

## Architecture

- **Library**: django-oauth-toolkit (DOT) 3.x
- **Flow**: Client Credentials (machine-to-machine) + PKCE (mobile app)
- **Scopes**: `read`, `write`
- **Token endpoint**: `/o/token/`
- **Settings**: `OAUTH2_PROVIDER` dict in `src/stt/settings.py`
- **Custom Validator**: `src/stt/api/oauth2_validators.py`

## Critical: CustomOAuth2Validator

### Why it exists

DOT 3.x explicitly sets `request.user = None` for `client_credentials` grant type inside its internal `_save_bearer_token` method **before** creating the `AccessToken`. This means all client_credentials tokens are created with `user=None`, which causes **HTTP 403** on any endpoint using `IsAuthenticated` or `TokenHasReadWriteScope` permissions.

### How it works

`CustomOAuth2Validator` overrides `_save_bearer_token` to:
1. Call the parent method (which creates the token with `user=None`)
2. Post-update the token via DB query to set `user` to the application's associated user

```python
# src/stt/api/oauth2_validators.py
class CustomOAuth2Validator(OAuth2Validator):
    def _save_bearer_token(self, token, request, *args, **kwargs):
        super()._save_bearer_token(token, request, *args, **kwargs)
        if request.grant_type == "client_credentials" and request.client.user:
            AccessToken.objects.filter(
                token=token["access_token"], user__isnull=True,
            ).update(user=request.client.user)
```

### Registration in settings.py

The validator MUST be registered inside the `OAUTH2_PROVIDER` dict:

```python
OAUTH2_PROVIDER = {
    ...
    "OAUTH2_VALIDATOR_CLASS": "stt.api.oauth2_validators.CustomOAuth2Validator",
}
```

## Known Pitfalls & Lessons Learned

### 1. OAUTH2_VALIDATOR_CLASS silently ignored

**Symptom**: Tokens created with `user=None`, HTTP 403 on API calls, no log output from CustomOAuth2Validator.

**Root cause**: The `OAUTH2_VALIDATOR_CLASS` key must be inside the `OAUTH2_PROVIDER` dict in `settings.py`. If the deployed `settings.py` is outdated (missing this key), DOT silently falls back to the default `OAuth2Validator` — no error, no warning.

**Diagnosis**:
```python
# In Django shell:
from django.conf import settings
print(settings.OAUTH2_PROVIDER.get('OAUTH2_VALIDATOR_CLASS'))
# → None means the key is missing from the deployed settings

from oauth2_provider.settings import oauth2_settings
print(oauth2_settings.OAUTH2_VALIDATOR_CLASS)
# → Should show CustomOAuth2Validator, NOT the default OAuth2Validator
```

**Fix**: Ensure `settings.py` is deployed with the `OAUTH2_VALIDATOR_CLASS` key and restart the server.

### 2. client_credentials tokens need an Application with a user

**Requirement**: The OAuth2 `Application` object must have a `user` field set (e.g. to the admin user). Without it, even with `CustomOAuth2Validator`, tokens will have `user=None` because `request.client.user` is `None`.

**Creating an Application correctly**:
```python
from oauth2_provider.models import Application
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.get(username='admin')
app = Application.objects.create(
    name="stt-cli",
    client_type=Application.CLIENT_CONFIDENTIAL,
    authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    user=admin,  # ← CRITICAL: must be set
)
print(f"client_id: {app.client_id}")
print(f"client_secret: {app.client_secret}")  # Save before it gets hashed
```

### 3. DOT 3.x hashes client secrets

DOT 3.x stores `client_secret` as a pbkdf2 hash (like Django passwords). The plaintext secret is only available at creation time. When sending token requests, always use the **plaintext** secret, not the hash.

### 4. Override `_save_bearer_token`, not other methods

Previous attempts that **did NOT work**:
- Overriding `_create_access_token` — DOT sets `user=None` **after** this method returns
- Overriding `save_bearer_token` — DOT 3.x calls internal `_save_bearer_token` instead
- The only reliable approach is overriding `_save_bearer_token` with a post-update DB query

### 5. Deployment: settings.py must be in sync

When deploying changes to OAuth2 settings:
1. Copy both `settings.py` AND `oauth2_validators.py` to the remote server
2. Restart the server (`docker compose restart stt-server`)
3. Verify with the Django shell diagnosis commands above
4. Delete old tokens and create a new one to test

## Files

| File | Purpose |
|------|---------|
| `src/stt/settings.py` | `OAUTH2_PROVIDER` dict with all DOT settings |
| `src/stt/api/oauth2_validators.py` | `CustomOAuth2Validator` class |
| `src/stt/api/views.py` | Views with `TokenHasReadWriteScope` permission |
| `tests/test_oauth2.py` | OAuth2 test suite |

## Checklist: After OAuth2 Changes

- [ ] `OAUTH2_VALIDATOR_CLASS` still points to `CustomOAuth2Validator` in settings
- [ ] `CustomOAuth2Validator._save_bearer_token` still post-updates user
- [ ] Tests pass: `docker compose exec stt-server pytest tests/test_oauth2.py -v`
- [ ] If deployed: verify with Django shell that `oauth2_settings.OAUTH2_VALIDATOR_CLASS` returns the custom class
- [ ] If deployed: test token acquisition + API access end-to-end
