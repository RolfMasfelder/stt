import os

from dotenv import load_dotenv
from faster_whisper import WhisperModel

# Load environment variables from .env file
load_dotenv()

model_name = os.getenv("WHISPER_MODEL", "small")
device = os.getenv("WHISPER_DEVICE", "cpu")
audio_file = os.getenv("AUDIO_INPUT_FILE", "meeting.wav")

model = WhisperModel(model_name, device=device)
segments, info = model.transcribe(audio_file)

transcript = " ".join([s.text for s in segments])
print(transcript)
