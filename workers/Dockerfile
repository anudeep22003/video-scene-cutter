FROM python:3.12-bookworm

# The Debian base supplies build tools for the Lambda runtime interface client.
# Install media binaries at build time, never during a Lambda invocation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg cmake libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /function
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt awslambdaric==3.1.1
COPY *.py ./workers/
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["workers.detect.handler"]
