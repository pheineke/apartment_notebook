FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies 
# Includes chromium and chromium-driver for seleniumbase to work on Raspberry Pi (ARM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Gunicorn for production serving, seleniumbase for the immoscout bypass
RUN pip install --no-cache-dir gunicorn seleniumbase

# Copy the application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application with Gunicorn
# -w 1 ensures only 1 worker runs, preventing the BackgroundScheduler from duplicating
# --threads 4 allows serving multiple requests concurrently within that single worker
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "app:app"]
