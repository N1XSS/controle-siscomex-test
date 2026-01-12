# Tutorial: Testes e Verificação do Sistema na VPS

Este tutorial explica como testar e verificar se o sistema está funcionando corretamente na VPS após o deploy no Dokploy.

## Índice

1. [Acessar o Container](#1-acessar-o-container)
2. [Verificar Status do Sistema](#2-verificar-status-do-sistema)
3. [Testar Conexão com PostgreSQL](#3-testar-conexão-com-postgresql)
4. [Executar Testes Básicos](#4-executar-testes-básicos)
5. [Verificar Agendamento (Cron)](#5-verificar-agendamento-cron)
6. [Monitorar Logs](#6-monitorar-logs)
7. [Comandos Úteis](#7-comandos-úteis)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Acessar o Container

### 1.1. Via Dokploy (Recomendado para Leigos)

1. Acesse o Dokploy no navegador
2. Vá para o seu projeto
3. Procure por **"Terminal"**, **"Shell"** ou **"Console"**
4. Clique para abrir o terminal integrado
5. Você já estará dentro do container

### 1.2. Via SSH na VPS (Avançado)

Se você tem acesso SSH à VPS:

```bash
# Conectar via SSH à VPS
ssh usuario@ip_da_vps

# Listar containers rodando
docker ps

# Acessar o container (substitua NOME_CONTAINER pelo nome do seu container)
docker exec -it NOME_CONTAINER /bin/bash
```

**Como descobrir o nome do container:**
```bash
docker ps | grep controle-siscomex
```

O nome aparecerá na primeira coluna (ex: `controle-siscomex` ou `controle-siscomex-xxx`).

### 1.3. Primeiro Passo Dentro do Container

Quando você entrar no container, verifique se está no diretório correto:

```bash
# Ver diretório atual
pwd

# Se não estiver em /app, vá para lá
cd /app

# Verificar arquivos
ls -la
```

Você deve ver arquivos como: `main.py`, `consulta_sap.py`, `db_manager.py`, etc.

---

## 2. Verificar Status do Sistema

Este comando mostra quantos dados estão no banco de dados (NFs, DUEs, etc.).

```bash
# Certifique-se de estar no diretório correto
cd /app

# Executar verificação de status
python3 main.py --status
```

**O que esperar:**
- Mostra quantidade de NFs do SAP
- Mostra quantidade de DUEs baixadas
- Mostra quantidade de itens e eventos
- Mostra DUEs que precisam ser atualizadas

**Exemplo de saída:**
```
============================================================
   GERENCIADOR DE SINCRONIZACAO DUE - SISCOMEX
============================================================
   Data/Hora: 12/01/2026 19:00:00
============================================================

[STATUS DO SISTEMA]
----------------------------------------
  NFs SAP: 1215 chaves
  Vinculos NF->DUE: 850 registros
  DUEs baixadas: 850 total
  Itens de DUE: 2100 registros
  ...
----------------------------------------
```

---

## 3. Testar Conexão com PostgreSQL

Para verificar se a conexão com o banco de dados está funcionando:

```bash
cd /app

# Teste rápido de conexão
python3 -c "from db_manager import db_manager; db_manager.conectar() and print('OK: Conectado!') or print('ERRO: Falha na conexão')"
```

**O que esperar:**
- `OK: Conectado!` = Conexão funcionando
- `ERRO: Falha na conexão` = Problema de conexão (verifique variáveis de ambiente)

---

## 4. Executar Testes Básicos

### 4.1. Testar Consulta SAP (AWS Athena)

Este teste consulta o AWS Athena e salva as NFs no PostgreSQL:

```bash
cd /app
python3 consulta_sap.py
```

**O que esperar:**
- Mensagens de progresso
- "Conectado ao AWS Athena"
- "Query executada com sucesso"
- "Total de chaves NF únicas encontradas: XXXX"
- "X chaves NF salvas no PostgreSQL"

**Tempo estimado:** 1-3 minutos

### 4.2. Testar Sincronização de Novas DUEs

Este teste consulta novas DUEs do Siscomex:

```bash
cd /app
python3 main.py --novas
```

**O que esperar:**
- "Sincronizando novas DUEs"
- Consulta de NFs no SAP
- Consulta de DUEs no Siscomex
- Mensagens de progresso
- Resumo final com quantidades

**Tempo estimado:** 5-15 minutos (depende da quantidade de NFs)

### 4.3. Testar Sincronização Completa (Recomendado)

Este teste executa todo o fluxo (consulta SAP + sincronização + atualização):

```bash
cd /app
python3 main.py --completo
```

**O que esperar:**
- Execução de todos os passos acima
- Pode demorar vários minutos
- Mostra progresso detalhado

**Tempo estimado:** 10-30 minutos (depende da quantidade de dados)

---

## 5. Verificar Agendamento (Cron)

O sistema está configurado para executar automaticamente **1x por dia às 06:00** (horário de Brasília).

### 5.1. Verificar Configuração do Cron

```bash
cd /app

# Ver arquivo de configuração do cron
cat /etc/cron.d/cron_job
```

**O que deve aparecer:**
```
0 6 * * * cd /app && /usr/local/bin/python3 main.py --completo >> /app/logs/cron.log 2>&1
```

Isso significa: executar todos os dias às 06:00.

### 5.2. Verificar Crontab Ativa

```bash
# Ver tabela crontab
crontab -l
```

Deve mostrar a mesma linha do arquivo acima.

### 5.3. Verificar se o Cron Está Rodando

```bash
# Ver processos do cron
ps aux | grep cron
```

Deve mostrar um processo `cron` rodando.

### 5.4. Verificar Horário do Sistema

```bash
# Ver data e hora atual
date
```

**Importante:** Deve estar em horário de Brasília (UTC-3).

**Exemplo:**
```
Mon Jan 12 19:00:00 -03 2026
```

O `-03` indica horário de Brasília (3 horas atrás do UTC).

### 5.5. Verificar Timezone

```bash
# Ver timezone configurado
echo $TZ

# Ou
cat /etc/timezone
```

Deve mostrar: `America/Sao_Paulo`

### 5.6. Verificar Tudo de Uma Vez

Execute este comando para ver tudo de uma vez:

```bash
cd /app && echo "=== VERIFICACAO DO CRON ===" && \
echo "" && \
echo "1. Arquivo cron_job:" && \
cat /etc/cron.d/cron_job && \
echo "" && \
echo "2. Crontab ativa:" && \
crontab -l && \
echo "" && \
echo "3. Processo cron:" && \
ps aux | grep -E "[c]ron" && \
echo "" && \
echo "4. Horario do sistema:" && \
date && \
echo "" && \
echo "5. Timezone:" && \
echo "TZ=$TZ" && \
echo "" && \
echo "6. Logs do cron:" && \
ls -lh /app/logs/cron.log 2>/dev/null || echo "Log ainda nao existe (normal se ainda nao executou)"
```

---

## 6. Monitorar Logs

### 6.1. Ver Logs do Cron (Execuções Agendadas)

```bash
cd /app

# Ver logs completos
cat /app/logs/cron.log

# Ver últimas 50 linhas
tail -50 /app/logs/cron.log

# Acompanhar em tempo real (atualiza automaticamente)
tail -f /app/logs/cron.log
```

Para sair do `tail -f`, pressione `Ctrl + C`.

### 6.2. Ver Logs no Dokploy

1. Acesse o Dokploy no navegador
2. Vá para o seu projeto
3. Clique em **"Logs"**
4. Veja os logs em tempo real

### 6.3. Verificar se o Log Foi Criado

```bash
# Verificar se o arquivo de log existe
ls -lh /app/logs/

# Ver quando foi modificado pela última vez
stat /app/logs/cron.log
```

---

## 7. Comandos Úteis

### 7.1. Verificar Variáveis de Ambiente

```bash
# Ver todas as variáveis PostgreSQL
env | grep POSTGRES

# Ver todas as variáveis AWS
env | grep AWS

# Ver todas as variáveis Siscomex
env | grep SISCOMEX

# Ver todas as variáveis (cuidado: mostra senhas!)
env
```

### 7.2. Testar Conexão Manual com PostgreSQL

```bash
cd /app

# Teste completo de conexão
python3 << 'EOF'
from db_manager import db_manager
import sys

print("Testando conexão com PostgreSQL...")
if db_manager.conectar():
    print("✓ Conexão OK!")
    db_manager.desconectar()
    sys.exit(0)
else:
    print("✗ Falha na conexão")
    sys.exit(1)
EOF
```

### 7.3. Ver Diretório de Trabalho

```bash
# Ver onde você está
pwd

# Ir para o diretório da aplicação
cd /app

# Listar arquivos
ls -la

# Ver apenas arquivos Python
ls -la *.py
```

### 7.4. Sair do Container

Quando terminar os testes:

```bash
exit
```

Ou pressione `Ctrl + D`

---

## 8. Troubleshooting

### 8.1. "python3: can't open file 'main.py'"

**Problema:** Você não está no diretório correto.

**Solução:**
```bash
cd /app
python3 main.py --status
```

### 8.2. "docker: command not found"

**Problema:** Você está DENTRO do container e tentou usar `docker exec`.

**Solução:** Quando está dentro do container, execute os comandos diretamente:
```bash
# ERRADO (dentro do container):
docker exec -it container python3 main.py --status

# CORRETO (dentro do container):
python3 main.py --status
```

### 8.3. "Falha ao conectar ao PostgreSQL"

**Problema:** Variáveis de ambiente não configuradas ou conexão falhando.

**Solução:**
1. Verificar variáveis: `env | grep POSTGRES`
2. Se faltarem variáveis, configure no Dokploy
3. Verificar logs do container no Dokploy

### 8.4. Cron Não Executou

**Problema:** O agendamento não executou no horário esperado.

**Verificações:**
1. Verificar se cron está rodando: `ps aux | grep cron`
2. Verificar horário do sistema: `date`
3. Verificar timezone: `echo $TZ`
4. Verificar configuração: `cat /etc/cron.d/cron_job`
5. Verificar logs: `cat /app/logs/cron.log`

### 8.5. Logs Não Aparecem

**Problema:** O arquivo de log não existe ou está vazio.

**Explicação:** O log só é criado quando o cron executa pela primeira vez. Se ainda não executou (não chegou às 06:00), o arquivo não existe ainda. Isso é normal.

**Para testar sem esperar:**
Execute manualmente:
```bash
cd /app
python3 main.py --completo >> /app/logs/cron.log 2>&1
```

Depois verifique:
```bash
cat /app/logs/cron.log
```

---

## Resumo Rápido

### Verificação Inicial (Recomendado)

```bash
# 1. Entrar no diretório
cd /app

# 2. Verificar status
python3 main.py --status

# 3. Verificar cron
cat /etc/cron.d/cron_job
crontab -l
ps aux | grep cron
date
```

### Teste Completo

```bash
# 1. Entrar no diretório
cd /app

# 2. Testar conexão
python3 -c "from db_manager import db_manager; db_manager.conectar() and print('OK') or print('ERRO')"

# 3. Executar sincronização completa
python3 main.py --completo

# 4. Verificar status novamente
python3 main.py --status
```

### Monitorar Execução

```bash
# Acompanhar logs em tempo real
tail -f /app/logs/cron.log
```

---

## Quando Usar Cada Comando

| Situação | Comando |
|----------|---------|
| Ver quantos dados estão no banco | `python3 main.py --status` |
| Testar se está tudo funcionando | `python3 main.py --completo` |
| Apenas buscar novas NFs do SAP | `python3 consulta_sap.py` |
| Apenas sincronizar novas DUEs | `python3 main.py --novas` |
| Verificar agendamento | `cat /etc/cron.d/cron_job` |
| Ver logs do cron | `cat /app/logs/cron.log` |
| Acompanhar logs em tempo real | `tail -f /app/logs/cron.log` |
| Verificar conexão com banco | `python3 -c "from db_manager import db_manager; db_manager.conectar()"` |

---

## Próximos Passos

Após verificar que tudo está funcionando:

1. **Deixe o sistema rodando** - O cron executará automaticamente todos os dias às 06:00
2. **Monitore os logs** - Verifique periodicamente se está executando corretamente
3. **Verifique status** - Execute `python3 main.py --status` periodicamente para ver o crescimento dos dados

---

## Ajuda Adicional

Se encontrar problemas não cobertos neste tutorial:

1. Verifique os logs no Dokploy (aba "Logs")
2. Consulte o arquivo `DEPLOY_DOKPLOY.md` para mais detalhes técnicos
3. Verifique as variáveis de ambiente no Dokploy
4. Entre em contato com o suporte técnico

---

**Última atualização:** 12/01/2026
