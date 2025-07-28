#################### STAGE 1: Go Builder ####################
#################### STAGE 1: Go Builder ####################
FROM --platform=linux/amd64 golang:1.21-alpine AS gobuilder

RUN apk add --no-cache binutils upx

WORKDIR /app
COPY go go
WORKDIR /app/go

RUN go mod tidy && \
    CGO_ENABLED=0 go build -ldflags="-s -w" -o /processor ./cmd/main.go && \
    strip /processor && \
    upx --ultra-brute /processor

#################### STAGE 2: Python Wheel Builder ####################
FROM --platform=linux/amd64 python:3.11-slim AS pybuilder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libmupdf-dev && \
    rm -rf /var/lib/apt/lists/*

COPY extractor/requirement.txt .
RUN pip wheel --no-deps --wheel-dir /build/wheels -r requirement.txt

COPY extractor/extract.py /build/extract.py

#################### STAGE 3: Final Runtime Image (Slim-Compatible) ####################
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Create runtime directories
RUN mkdir -p /app/input /app/output /app/temp_output /extractor

# Copy Go binary
COPY --from=gobuilder /processor /app/processor

# Copy extractor script
COPY --from=pybuilder /build/extract.py /extractor/extract.py

# Install only required wheel
COPY --from=pybuilder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/PyMuPDF*.whl && \
    rm -rf /tmp/wheels

# Clean everything else
RUN rm -rf /root/.cache /usr/share/doc /usr/share/man /usr/share/locale \
    /usr/lib/python3.11/test /usr/lib/python3.11/__pycache__ \
    /usr/lib/python3.11/site-packages/__pycache__ \
    /var/cache /var/log /tmp/*

ENTRYPOINT ["/app/processor"]

