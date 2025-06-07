# Use official Python image
FROM python:3.12-slim

# System dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg gcc && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependencies and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Give execution rights
RUN chmod +x start.sh

# Run the bot
CMD ["bash", "start.sh"]
