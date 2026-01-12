FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY *.py ./

# Criar diretório para logs e dados (se necessário)
RUN mkdir -p /app/logs /app/dados

# Criar script de agendamento
COPY cron_job.sh /etc/cron.d/cron_job
RUN chmod 0644 /etc/cron.d/cron_job && \
    crontab /etc/cron.d/cron_job

# Criar script de entrada
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

# Script de entrada
ENTRYPOINT ["/entrypoint.sh"]

# Comando padrão (mantém container rodando)
CMD ["cron", "-f"]
