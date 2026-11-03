# DeepFake Shield API: CPU inference image for Google Cloud Run.
# Build from the repository root (the image needs backend/, ml/ and models/):
#   docker build -f backend/Dockerfile -t deepfake-shield-api .
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Match the 2 vCPUs the service is deployed with; torch otherwise sizes its pool to the host.
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    # Safe defaults for a public deployment; override with --set-env-vars.
    SYNC_ANALYSIS=true \
    PROTECT_LIST=true \
    TRUST_X_FORWARDED_FOR=true \
    RATE_LIMIT_PER_HOUR=20 \
    DEEPFAKE_SHIELD_MAX_UPLOAD_BYTES=32000000 \
    PORT=8080

WORKDIR /srv/backend

# CPU-only torch wheels: no CUDA libraries in the image.
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.14.1" "torchvision==0.29.1"
COPY backend/requirements-deploy.txt /tmp/requirements-deploy.txt
RUN pip install -r /tmp/requirements-deploy.txt

# Layout mirrors the repository: video_detector.py resolves ml/ and models/ from the project root.
# --chmod makes the files world-readable regardless of the source filesystem (exFAT checkouts are 0700).
# The directories are created first: COPY would create missing parents with the file mode (0644).
RUN mkdir -p /srv/ml/data /srv/ml/models /srv/models
COPY --chown=root:root --chmod=0644 ml/data/video_dataset.py /srv/ml/data/video_dataset.py
COPY --chown=root:root --chmod=0644 ml/models/efficientnet_baseline.py ml/models/video_heads.py /srv/ml/models/
COPY --chown=root:root --chmod=0644 models/deepfake_shield_video_v1.pt \
     models/deepfake_shield_meanpool_mlp_v1.pt \
     models/deepfake_shield_temporal_v1.pt \
     /srv/models/
COPY --chown=root:root --chmod=0755 backend/app /srv/backend/app

RUN useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin app
USER app

EXPOSE 8080
# One worker: records live in process memory and the inference lock is per process.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT}\" --workers 1 --timeout-keep-alive 30"]
