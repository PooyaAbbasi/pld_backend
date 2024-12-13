# Prepare python image
FROM python:3.12

# setting environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN python -m pip install --upgrade pip

### preparing requirements
WORKDIR /usr/src/app
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# copy files
COPY . .

# expose listening port
EXPOSE 8000
