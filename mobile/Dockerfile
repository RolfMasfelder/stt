FROM debian:bookworm-slim

# Avoid interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Build arg for host user/group ID mapping
ARG HOST_UID=1000
ARG HOST_GID=100

# Install base dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev \
    liblzma-dev \
    libstdc++-12-dev \
    openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# Set Java home
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Install Android SDK command-line tools
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=$ANDROID_HOME
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \
    curl -fsSL https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -o /tmp/cmdline-tools.zip && \
    unzip -q /tmp/cmdline-tools.zip -d $ANDROID_HOME/cmdline-tools && \
    mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && \
    rm /tmp/cmdline-tools.zip

ENV PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

# Accept Android SDK licenses and install required SDK components
RUN yes | sdkmanager --licenses > /dev/null 2>&1 && \
    sdkmanager --install \
    "platform-tools" \
    "platforms;android-35" \
    "build-tools;35.0.0"

# Install Flutter SDK
ENV FLUTTER_HOME=/opt/flutter
ENV PATH="$FLUTTER_HOME/bin:$FLUTTER_HOME/bin/cache/dart-sdk/bin:$PATH"
RUN git clone --depth 1 --branch stable https://github.com/flutter/flutter.git $FLUTTER_HOME && \
    flutter precache && \
    flutter config --no-analytics && \
    dart --disable-analytics

# Create non-root user matching host UID/GID
RUN groupadd -g $HOST_GID appuser 2>/dev/null || true && \
    useradd -m -u $HOST_UID -g $HOST_GID -s /bin/bash appuser && \
    chmod -R a+rw $FLUTTER_HOME && \
    chmod -R a+r $ANDROID_HOME && \
    mkdir -p /home/appuser/.pub-cache /home/appuser/.gradle && \
    chown -R appuser:$HOST_GID /home/appuser

# Flutter/Android SDK writable dirs need user access
ENV PUB_CACHE=/home/appuser/.pub-cache

USER appuser

# Git safe.directory for Flutter SDK (owned by root, accessed by appuser)
RUN git config --global --add safe.directory /opt/flutter

WORKDIR /app

CMD ["bash"]
