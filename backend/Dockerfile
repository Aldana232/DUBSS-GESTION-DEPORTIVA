# ─── Imagen de PRODUCCIÓN del backend (Django + Gunicorn; la usan también Celery worker y beat) ───
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl (healthcheck) y gosu (bajar de root a un usuario sin privilegios). Las dependencias Python traen binarios ya compilados.
RUN apt-get update && apt-get install -y --no-install-recommends curl gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt constraints.txt ./
RUN pip install -r requirements.txt -c constraints.txt

COPY . .

# Usuario sin privilegios. El contenedor ARRANCA como root solo para corregir el dueño de los volúmenes
# (estáticos, subidas y modelos de IA) y enseguida baja a «dubss»: ver docker-entrypoint.sh.
RUN addgroup --system dubss && adduser --system --ingroup dubss --home /home/dubss dubss \
    && mkdir -p /app/staticfiles /app/mediafiles /app/apps/ml/models_trained /home/dubss \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R dubss:dubss /app /home/dubss

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--no-control-socket"]
