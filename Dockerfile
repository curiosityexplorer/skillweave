FROM python:3.11-slim

WORKDIR /app

# Copy source code
COPY src/ src/
COPY experiments/ experiments/
COPY requirements.txt .

# Install dependencies (none required for core experiments)
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Create results directory
RUN mkdir -p results/raw results/aggregated

# Default: run all experiments
CMD ["python", "experiments/run_experiments.py", "--seed", "42"]
