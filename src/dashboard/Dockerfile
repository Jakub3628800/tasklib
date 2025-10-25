FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY requirements.txt .
COPY app.py .
COPY models.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8989

# Run the app
CMD ["python", "app.py"]
