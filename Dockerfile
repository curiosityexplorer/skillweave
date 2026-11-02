FROM python:3.11-slim

WORKDIR /app

# Copy source code
COPY src/ src/
COPY experiments/ experiments/
COPY requirements.txt .

# Install dependencies (none required for core experiments)
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Create results directory
RUN mkdir -p results_v3/raw results_v3/aggregated

# Default: run all experiments
CMD ["sh", "-c", "python experiments/run_threat_coverage.py --out results_v3 && python experiments/run_scalability_v3.py --out results_v3"]
