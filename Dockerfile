# --- Stage 1: Build the Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend

# Copy frontend source and configuration
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY frontend/ ./
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
RUN npm run build

# --- Stage 2: Build the Backend and Serve ---
FROM python:3.12-slim
WORKDIR /app

# Ensure we have essential tools if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Copy the built frontend from Stage 1 into the backend's expected directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose the API port (Hugging Face default is 7860)
EXPOSE 7860

# Run the FastAPI server via Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
