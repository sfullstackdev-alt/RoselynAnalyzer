FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and .NET SDK
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Install .NET SDK 8 and 10
RUN wget https://dot.net/v1/dotnet-install.sh -O dotnet-install.sh \
    && chmod +x dotnet-install.sh \
    && ./dotnet-install.sh --channel 8.0 --install-dir /usr/share/dotnet \
    && ./dotnet-install.sh --channel 10.0 --install-dir /usr/share/dotnet \
    && ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet \
    && rm dotnet-install.sh

# Create repos directory
RUN mkdir -p /app/repos

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e .

# Set the entrypoint
ENTRYPOINT ["roselyn"]
