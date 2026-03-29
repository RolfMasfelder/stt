"""DRF serializers for request/response validation and OpenAPI documentation."""

from rest_framework import serializers

# --- Input serializers ---


class AudioUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Audio file (.wav, .mp3, .flac, .ogg, .m4a, .wma, .webm)",
    )
    model = serializers.CharField(
        default="small",
        help_text="Whisper model name",
    )


class ProcessUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Audio file (.wav, .mp3, .flac, .ogg, .m4a, .wma, .webm)",
    )
    model = serializers.CharField(
        default="small",
        help_text="Whisper model name",
    )
    diarize = serializers.BooleanField(
        default=True,
        help_text="Enable speaker diarization",
    )


# --- Output serializers ---


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class TranscribeResponseSerializer(serializers.Serializer):
    text = serializers.CharField()


class DiarizedSegmentSerializer(serializers.Serializer):
    speaker = serializers.CharField()
    start = serializers.FloatField()
    end = serializers.FloatField()
    text = serializers.CharField()


class DiarizeResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    diarized_text = serializers.CharField()
    segments = DiarizedSegmentSerializer(many=True)


class ProcessResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    diarized_text = serializers.CharField(allow_null=True)
    structured_text = serializers.CharField()
    summary = serializers.CharField()


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
