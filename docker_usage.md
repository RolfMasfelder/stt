# Development (uses host networking, connects to local LM Studio)
docker-compose --profile dev up stt-dev

# Production (full container setup)
docker-compose --profile production up

# Build and run specific service
docker-compose build stt
docker-compose run stt python transkribe.py
