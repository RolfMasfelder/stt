"""HTTP client for the remote STT server."""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from stt.config import OAuth2ClientConfig
from stt.whisper_common import convert_to_whisper_format

logger = logging.getLogger(__name__)


class ClientError(Exception):
    """Raised when a request to the STT server fails!"""


class AuthenticationError(ClientError):
    """Raised when OAuth2 authentication fails."""


@dataclass
class DiarizedResult:
    """Result from the diarize endpoint."""

    text: str
    diarized_text: str
    segments: list[dict]


@dataclass
class ProcessResult:
    """Result from the process endpoint."""

    text: str
    diarized_text: str | None
    structured_text: str
    summary: str


class STTClient:
    """Client for the remote STT server API with OAuth2 authentication."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 600,
        oauth2: OAuth2ClientConfig | None = None,
        verify: bool | str = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._oauth2 = oauth2
        self._verify = verify
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    def _fetch_token(self) -> str:
        """Obtain an access token via OAuth2 Client Credentials flow."""
        if not self._oauth2 or not self._oauth2.token_url:
            raise AuthenticationError(
                "OAuth2 not configured (OAUTH2_TOKEN_URL missing)"
            )

        logger.info("Requesting OAuth2 token from %s", self._oauth2.token_url)
        try:
            resp = requests.post(
                self._oauth2.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._oauth2.client_id,
                    "client_secret": self._oauth2.client_secret,
                    "scope": self._oauth2.scopes,
                },
                timeout=30,
                verify=self._verify,
            )
        except requests.RequestException as e:
            raise AuthenticationError(f"Token request failed: {e}") from e

        if resp.status_code != 200:
            raise AuthenticationError(
                f"Token request returned HTTP {resp.status_code}: {resp.text}"
            )

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise AuthenticationError("No access_token in token response")

        expires_in = data.get("expires_in", 900)
        # Refresh 30s before actual expiry to avoid race conditions
        self._token_expires_at = time.monotonic() + expires_in - 30
        self._access_token = token
        logger.info("OAuth2 token acquired (expires_in=%ds)", expires_in)
        return token

    def _get_token(self) -> str | None:
        """Return a valid access token, fetching/refreshing as needed."""
        if self._oauth2 is None or not self._oauth2.token_url:
            return None

        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        return self._fetch_token()

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header if OAuth2 is configured."""
        token = self._get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _post_file(self, endpoint: str, audio_file: Path, data: dict) -> dict:
        """Send an audio file to a server endpoint and return the JSON response."""
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        converted = convert_to_whisper_format(audio_file)
        cleanup = converted != audio_file

        url = f"{self.base_url}{endpoint}"
        logger.info("Sending request to %s", url)

        try:
            with open(converted, "rb") as f:
                files = {"file": (audio_file.name, f)}
                try:
                    resp = requests.post(
                        url,
                        files=files,
                        data=data,
                        headers=self._auth_headers(),
                        timeout=self.timeout,
                        verify=self._verify,
                    )
                except requests.RequestException as e:
                    raise ClientError(f"Request to {url} failed: {e}") from e
        finally:
            if cleanup:
                converted.unlink(missing_ok=True)

        if resp.status_code == 401:
            raise AuthenticationError(f"Authentication failed (HTTP 401): {resp.text}")

        if resp.status_code != 200:
            raise ClientError(f"Server returned HTTP {resp.status_code}: {resp.text}")

        return resp.json()

    def health(self) -> bool:
        """Check if the server is healthy."""
        try:
            resp = requests.get(
                f"{self.base_url}/health",
                headers=self._auth_headers(),
                timeout=10,
                verify=self._verify,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def transcribe(self, audio_file: Path, model: str = "small") -> str:
        """Transcribe an audio file on the remote server.

        Returns:
            The transcribed text.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ClientError: If the server request fails.
        """
        body = self._post_file("/v1/transcribe", audio_file, {"model": model})
        return body["text"]

    def diarize(self, audio_file: Path, model: str = "small") -> DiarizedResult:
        """Transcribe and diarize an audio file on the remote server.

        Returns:
            DiarizedResult with text, diarized_text and segments.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ClientError: If the server request fails.
        """
        body = self._post_file("/v1/diarize", audio_file, {"model": model})
        return DiarizedResult(
            text=body["text"],
            diarized_text=body["diarized_text"],
            segments=body["segments"],
        )

    def process(
        self, audio_file: Path, model: str = "small", diarize: bool = True
    ) -> ProcessResult:
        """Run the full pipeline on the remote server.

        Returns:
            ProcessResult with text, diarized_text, structured_text and summary.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ClientError: If the server request fails.
        """
        data = {"model": model, "diarize": str(diarize).lower()}
        body = self._post_file("/v1/process", audio_file, data)
        return ProcessResult(
            text=body["text"],
            diarized_text=body.get("diarized_text"),
            structured_text=body["structured_text"],
            summary=body["summary"],
        )
