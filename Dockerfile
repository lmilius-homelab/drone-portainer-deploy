FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pi install --no-cache-dir -r requirements.txt

COPY plugin.py

ENTRYPOINT ["python", "/usr/src/app/plugin.py"]