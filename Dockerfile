FROM python:3.11-slim

ENV PATH="$PATH:/root/.local/bin"

### 2. Get Java via the package manager
RUN apt-get update && apt-get install -y \
build-essential \
curl \
openjdk-17-jre

WORKDIR /cprex

# install poetry
RUN pip install pipx
RUN pipx install poetry
RUN pipx ensurepath

# install dependencies and project
# COPY ./pyproject.toml ./poetry.lock /cprex/
COPY . /cprex/
RUN poetry install --no-dev --no-interaction --no-ansi --with models

# Expose streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["poetry", "run", "streamlit", "run", "cprex/ui/streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
