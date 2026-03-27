"""HTTP client for the remote STT server."""

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from stt.whisper_common import convert_to_whisper_format

logger = logging.getLogger(__name__)


class ClientError(Exception):
    """Raised when a request to the STT server fails."""


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
    """Client for the remote STT server API."""

    def __init__(self, base_url: str, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post_file(self, endpoint: str, audio_file: Path, data: dict) -> dict:
        """Send an audio file to a server endpoint and return the JSON response.

        Converts audio to whisper-native format (16kHz mono) before upload
        to reduce transfer size and processing time.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ClientError: If the server request fails.
        """
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
                        url, files=files, data=data, timeout=self.timeout
                    )
                except requests.RequestException as e:
                    raise ClientError(f"Request to {url} failed: {e}") from e
        finally:
            if cleanup:
                converted.unlink(missing_ok=True)

        if resp.status_code != 200:
            raise ClientError(f"Server returned HTTP {resp.status_code}: {resp.text}")

        return resp.json()

    def health(self) -> bool:
        """Check if the server is healthy."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=10)
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
