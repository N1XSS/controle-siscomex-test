# Agendamento para sincronização diária do sistema DUE
# Executa uma vez por dia às 06:00 (horário de Brasília)
# Formato: minuto hora dia mes dia-semana comando
0 6 * * * cd /app && /usr/local/bin/python3 -m src.main --completo >> /app/logs/cron.log 2>&1

# Opcional: Executar apenas sincronização de novas DUEs a cada 6 horas
# 0 */6 * * * cd /app && /usr/local/bin/python3 -m src.main --novas >> /app/logs/cron.log 2>&1

# Opcional: Executar apenas atualização de DUEs existentes às 02:00
# 0 2 * * * cd /app && /usr/local/bin/python3 -m src.main --atualizar >> /app/logs/cron.log 2>&1
