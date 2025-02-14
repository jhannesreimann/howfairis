FROM python:3.10.6-alpine3.16

WORKDIR /app

# Kopiere nur die notwendigen Dateien
COPY requirements.txt .
COPY main.py .
COPY howfairis/ howfairis/

# Installiere Abhängigkeiten
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt

# Port für die API
EXPOSE 80

# Starte die FastAPI-Anwendung
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
