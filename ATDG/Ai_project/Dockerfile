
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-liberation \
        libpangocairo-1.0-0 \
        libcairo2-dev \
        gcc \
        g++ \
        pkg-config \
        bash \
        libssl-dev \
        libffi-dev \
        curl \
        git \
        make \
        cmake \
        build-essential \
        python3-dev \
        # Tree-sitter build dependencies
        libtree-sitter-dev \
        # WeasyPrint dependencies (for advanced PDF generation)
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        libjpeg-dev \
        libopenjp2-7-dev \
        libtiff-dev \
        # Additional dependencies for tree-sitter languages
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Ensure tree-sitter languages are properly built with improved error handling
RUN python -c "import tree_sitter; import tree_sitter_languages; print('Tree-sitter and languages loaded successfully')" || \
    (echo "Failed to load tree-sitter-languages, trying alternative installation..." && \
     pip uninstall -y tree-sitter tree-sitter-languages tree-sitter-java && \
     pip install --no-cache-dir tree-sitter==0.20.4 tree-sitter-languages==1.6.1 tree-sitter-java && \
     python -c "import tree_sitter; import tree_sitter_languages; print('Alternative installation successful')")

COPY . /app/

# Tree-sitter tests moved to runtime (require Django setup)
# Test files are available in core_ai/tests/ for manual testing after container starts

RUN chmod +x /app/entrypoint.sh && \
    sed -i 's/\r$//' /app/entrypoint.sh 2>/dev/null || true

EXPOSE 8000

# لا نضع CMD هنا، Docker Compose هو من سيحدد الـ command لكل خدمة
# ENTRYPOINT و CMD في Dockerfile هما فقط Default
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"] 