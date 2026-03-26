# zum abholen von Youtube


yt-dlp -x --audio-format wav \
  --postprocessor-args "-ar 16000 -ac 1" \
  <URL>
