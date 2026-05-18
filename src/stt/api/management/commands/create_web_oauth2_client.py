"""Management command: register (or show) the Flutter-web OAuth2 client.

Creates a public Authorization-Code + PKCE application whose redirect URI
points to the Flutter web dev server (http://localhost:5000/callback).
Safe to run multiple times — skips creation if an app with the same client_id
already exists.

Usage:
    docker compose exec stt-server python manage.py create_web_oauth2_client
"""

from django.core.management.base import BaseCommand
from oauth2_provider.models import get_application_model

Application = get_application_model()

_CLIENT_ID = "flutter-web-dev"
_REDIRECT_URI = "http://localhost:5000/callback"


class Command(BaseCommand):
    help = "Register the Flutter-web OAuth2 client (PKCE, public, Authorization Code)."

    def handle(self, *args: object, **options: object) -> None:
        app, created = Application.objects.get_or_create(
            client_id=_CLIENT_ID,
            defaults={
                "name": "Flutter Web Dev",
                "client_type": Application.CLIENT_PUBLIC,
                "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
                "redirect_uris": _REDIRECT_URI,
                "skip_authorization": False,
                "algorithm": "",  # default (no JWT)
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created OAuth2 app '{app.name}' (client_id={app.client_id})"
                )
            )
        else:
            # Ensure redirect URI is up-to-date
            if _REDIRECT_URI not in app.redirect_uris:
                app.redirect_uris = _REDIRECT_URI
                app.save(update_fields=["redirect_uris"])
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated redirect URI for existing app '{app.name}'"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"App '{app.name}' already exists — no changes needed."
                    )
                )

        self.stdout.write("")
        self.stdout.write("── Flutter Web OAuth2 Client ──────────────────────────")
        self.stdout.write(f"  Client ID    : {app.client_id}")
        self.stdout.write(f"  Redirect URI : {_REDIRECT_URI}")
        self.stdout.write("  Grant type   : Authorization Code + PKCE")
        self.stdout.write("  Client type  : Public (no secret)")
        self.stdout.write("────────────────────────────────────────────────────────")
        self.stdout.write("")
        self.stdout.write("Configure the app in the browser Settings screen:")
        self.stdout.write("  Server URL : http://localhost:8090")
        self.stdout.write(f"  Client ID  : {app.client_id}")
