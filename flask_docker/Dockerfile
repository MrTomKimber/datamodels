FROM python:3.10.4-slim as base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

FROM base AS python-deps



# Install pipenv and compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev
RUN apt-get install graphviz
RUN pip install pipenv

# Install python dependencies in /.venv
COPY Pipfile .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/src"

FROM runtime as op-env
RUN mkdir /data
WORKDIR /app
#EXPOSE 5000