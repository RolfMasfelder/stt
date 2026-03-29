# Example of speaker diarization using pyannote.audio
# instantiate the pipeline
import os

from dotenv import load_dotenv
from pyannote.audio import Pipeline

load_dotenv()

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=os.environ["HF_STT_TOKEN"],
)

# run the pipeline on an audio file
diarization = pipeline("audio.wav")

# dump the diarization output to disk using RTTM format
with open("audio.rttm", "w") as rttm:
    diarization.write_rttm(rttm)
