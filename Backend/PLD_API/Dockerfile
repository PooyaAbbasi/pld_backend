## Prepare python image
##
##### ____ prodoction level Dockerfile ______ ######
#FROM python:3.12
#
## setting environment variables
#ENV PYTHONDONTWRITEBYTECODE=1
#ENV PYTHONUNBUFFERED=1
#
#
#RUN python -m pip install --upgrade pip
#
#### preparing requirements
#WORKDIR /usr/src/app
#COPY requirements.txt ./
#
#RUN pip install --no-cache-dir -r requirements.txt
#
## copy files
#COPY . .
#
## expose listening port
#EXPOSE 8000
#
#
## superuser credentials for initialization
#ENV SUPERUSER_USERNAME=super_admin
#ENV SUPERUSER_PASSWORD=s_u_@
### these credentials can be overrided within docker-compose.yml

### run initializaiton script
#RUN python manage.py migrate --noinput && python initialization.py
######################################
######################################

# Stage 1: Base build stage
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    build-essential \
    libmariadb-dev-compat \
    python3-dev \
    default-libmysqlclient-dev  \
    && rm -rf /var/lib/apt/lists/* \

# Create the app directory
RUN mkdir /app

# Set the working directory
WORKDIR /app

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Upgrade pip and install dependencies
RUN pip install --upgrade pip

# Copy the requirements file first (better caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libmariadb-dev \
    build-essential \
    libmariadb-dev-compat \
    python3-dev \
    default-libmysqlclient-dev  \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#RUN useradd -m -r appuser && \
#   mkdir /app && \
#   chown -R appuser /app

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set the working directory
WORKDIR /usr/src/app/

## Copy application code
#COPY --chown=appuser:appuser . .
COPY . .


# Switch to non-root user
#USER appuser

# Expose the application port
EXPOSE 8000

# superuser credentials for initialization
ENV SUPERUSER_USERNAME=super_admin
ENV SUPERUSER_PASSWORD=s_u_@
ENV DJANGO_SETTINGS_MODULE=PLD_API.settings
## these credentials can be overrided within docker-compose.yml


#CMD python manage.py migrate --noinput && \
# python initialization.py && \
# gunicorn PLD_API.asgi:application -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000

#CMD ["python", "-m", "manage.py", "runserver", "0.0.0.0:8000"]


