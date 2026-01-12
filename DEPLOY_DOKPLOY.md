# Deploy no Dokploy - Sistema de Controle DUE

Este guia explica como fazer o deploy do sistema na VPS usando o Dokploy.

## Pré-requisitos

1. VPS com Dokploy instalado e configurado
2. Acesso SSH à VPS
3. PostgreSQL acessível (na VPS ou externo)
4. Credenciais configuradas (Siscomex, PostgreSQL, AWS Athena)

## Passo 1: Configurar Repositório

1. Faça push do código para o GitHub/GitLab/Bitbucket
2. No Dokploy, crie um novo projeto
3. Conecte o repositório ao Dokploy

## Passo 2: Configurar Variáveis de Ambiente

**IMPORTANTE**: No Dokploy, configure as variáveis de ambiente na seção "Environment Variables" do projeto. **NÃO** crie arquivo `.env` dentro do container.

### Variáveis Obrigatórias - PostgreSQL

**Se o PostgreSQL está na MESMA VPS:**

Existem 3 cenários possíveis:

#### 1. PostgreSQL em container Docker (mesma VPS)
Se o PostgreSQL está rodando em um container Docker na mesma VPS, você tem duas opções:

**Opção A - Usar nome do serviço Docker:**
```
POSTGRES_HOST=postgres  # ou nome_do_servico_postgres
POSTGRES_PORT=5432      # porta padrão do PostgreSQL
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

**Opção B - Usar IP do container:**
Descubra o IP do container PostgreSQL:
```bash
docker inspect nome_container_postgres | grep IPAddress
```
Depois use:
```
POSTGRES_HOST=172.17.0.2  # IP do container PostgreSQL
POSTGRES_PORT=5432
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

#### 2. PostgreSQL criado como Database no Dokploy ⭐ **SEU CASO**

Quando você cria um Database PostgreSQL no Dokploy, o Dokploy automaticamente:
- Cria um container PostgreSQL gerenciado
- Cria variáveis de ambiente de conexão que podem ser vinculadas ao seu aplicativo

**Passos para configurar:**

1. **No Dokploy, no seu projeto (aplicação):**
   - Vá em **"Settings"** ou **"Environment Variables"**
   - Procure por **"Link Database"** ou **"Add Database Connection"**
   - Selecione o database PostgreSQL que você criou
   - O Dokploy automaticamente adiciona variáveis como `DATABASE_URL`, `DB_HOST`, `DB_PORT`, etc.

2. **Se o Dokploy usar variáveis padrão, configure manualmente:**
   
   O Dokploy geralmente cria variáveis no formato:
   ```
   POSTGRES_HOST=nome_do_database_service  # nome do serviço do database
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres  # ou o usuário que você configurou
   POSTGRES_PASSWORD=senha_gerada_pelo_dokploy
   POSTGRES_DB=nome_do_database
   ```

3. **Alternativa - Usar nome do serviço:**
   
   Se o Dokploy criar o database com um nome de serviço (ex: `postgres-123`), você pode usar:
   ```
   POSTGRES_HOST=postgres-123  # nome do serviço do database no Dokploy
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=senha_do_database
   POSTGRES_DB=nome_do_database
   ```

**💡 DICA**: No Dokploy, vá na página do seu Database PostgreSQL e procure por:
- **"Connection String"** ou **"Connection Info"**
- **"Internal URL"** ou **"Service Name"**
- Use essas informações para configurar as variáveis

#### 3. PostgreSQL rodando diretamente na VPS (não containerizado)

**Se o Dokploy usa rede Docker padrão:**
```
POSTGRES_HOST=host.docker.internal  # Acesso ao host da VPS
POSTGRES_PORT=5440                  # Porta do PostgreSQL na VPS
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

**Se o Dokploy permite usar network_mode: host:**
No Dokploy, configure o container para usar `network_mode: host` e então:
```
POSTGRES_HOST=localhost  # ou 127.0.0.1
POSTGRES_PORT=5440
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

#### 3. PostgreSQL externo (outra VPS/servidor)
```
POSTGRES_HOST=31.97.22.234  # IP externo
POSTGRES_PORT=5440
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

**⚠️ DICA**: Para descobrir qual opção usar:
1. Se o PostgreSQL está em container Docker: use o nome do serviço ou IP do container
2. Se está rodando diretamente na VPS: use `host.docker.internal` (padrão) ou `localhost` (se usar network_mode: host)
3. Teste a conexão: `docker exec -it nome_container python3 -c "from db_manager import db_manager; db_manager.conectar()"`

### Variáveis Obrigatórias - Credenciais Siscomex

```
SISCOMEX_CLIENT_ID=seu_client_id
SISCOMEX_CLIENT_SECRET=seu_client_secret
```

### Variáveis Obrigatórias - AWS Athena

```
AWS_ACCESS_KEY=sua_aws_access_key
AWS_SECRET_KEY=sua_aws_secret_key
AWS_REGION=us-east-1
ATHENA_CATALOG=AwsDataCatalog
ATHENA_DATABASE=default
ATHENA_WORKGROUP=primary
S3_OUTPUT_LOCATION=s3://locks-query-result/athena_odbc/
```

### Variáveis Opcionais

```
TZ=America/Sao_Paulo
PYTHONUNBUFFERED=1
```

### Como Configurar no Dokploy

1. No projeto, vá em **"Environment Variables"** ou **"Env"**
2. Clique em **"Add Variable"**
3. Adicione cada variável (nome e valor)
4. Salve as alterações
5. Faça **redeploy** do container para aplicar as mudanças

## Passo 3: Configurar Build

No Dokploy:

1. **Build Type**: Dockerfile
2. **Dockerfile Path**: `Dockerfile`
3. **Build Context**: `.`
4. **Port**: (Deixe vazio, este é um serviço sem exposição de porta)

## Passo 4: Configurar Deploy

1. **Service Type**: Application
2. **Restart Policy**: unless-stopped
3. **Health Check**: (Opcional, mas recomendado)

## Passo 5: Primeira Execução

Após o deploy:

1. **Verificar logs**: Acesse os logs no Dokploy para verificar se há erros
2. **Executar setup do banco** (se necessário):
   ```bash
   docker exec -it controle-siscomex python3 -c "from db_manager import db_manager; db_manager.conectar(); db_manager.criar_tabelas(); db_manager.desconectar()"
   ```
3. **Testar sincronização manual** (opcional):
   ```bash
   docker exec -it controle-siscomex python3 main.py --status
   ```

## Agendamento

O sistema está configurado para executar automaticamente **1x por dia às 06:00** (horário de Brasília).

### Alterar Horário do Agendamento

Para alterar o horário, edite o arquivo `cron_job.sh`:

```bash
# Formato: minuto hora dia mes dia-semana comando
0 6 * * *  # Executa às 06:00 todos os dias
0 2 * * *  # Executa às 02:00 todos os dias
0 */6 * * * # Executa a cada 6 horas
```

Após alterar, faça rebuild do container.

### Verificar Execuções

Para verificar os logs das execuções agendadas:

```bash
docker exec -it controle-siscomex tail -f /app/logs/cron.log
```

## Comandos Úteis

### Executar sincronização manual
```bash
docker exec -it controle-siscomex python3 main.py --completo
```

### Executar apenas novas DUEs
```bash
docker exec -it controle-siscomex python3 main.py --novas
```

### Executar apenas atualização
```bash
docker exec -it controle-siscomex python3 main.py --atualizar
```

### Verificar status
```bash
docker exec -it controle-siscomex python3 main.py --status
```

### Acessar shell do container
```bash
docker exec -it controle-siscomex /bin/bash
```

## Monitoramento

1. **Logs no Dokploy**: Acesse a aba de logs no Dokploy
2. **Logs do cron**: `/app/logs/cron.log` dentro do container
3. **Status do banco**: Use `python3 main.py --status` para ver estatísticas

## Troubleshooting

### Container não inicia
- Verifique os logs no Dokploy
- Verifique se todas as variáveis de ambiente obrigatórias estão configuradas
- Verifique se as variáveis foram salvas corretamente no Dokploy

### Erro: "Arquivo .env ou config.env nao encontrado"
- **Isso é NORMAL no Docker!** O sistema funciona com variáveis de ambiente do Dokploy
- Verifique se as variáveis estão configuradas no Dokploy (não precisa de arquivo .env)

### Erro: "connection to server at ... failed: timeout expired"

Este erro indica que o container não consegue alcançar o PostgreSQL. Possíveis causas:

#### 1. PostgreSQL externo (IP remoto)
Se você está usando um PostgreSQL externo (IP remoto, não local):

**Problemas comuns:**
- **Firewall bloqueando**: O firewall pode estar bloqueando conexões do container para o PostgreSQL
- **PostgreSQL não aceita conexões remotas**: O PostgreSQL pode estar configurado apenas para localhost
- **Rede do Docker**: O container pode não ter acesso à rede externa

**Soluções:**

**A. Verificar conectividade do container:**
```bash
# Acessar o container
docker exec -it nome_container /bin/bash

# Testar conectividade
nc -zv 31.97.22.234 5440
# ou
telnet 31.97.22.234 5440
```

**B. Se a conectividade falhar:**
- Verifique se o PostgreSQL aceita conexões remotas:
  - No servidor do PostgreSQL, edite `postgresql.conf`: `listen_addresses = '*'`
  - Edite `pg_hba.conf` para permitir conexões do IP da VPS:
    ```
    host    all    all    IP_DA_VPS/32    md5
    ```
- Verifique firewall do servidor PostgreSQL:
  - Libere a porta 5440 para o IP da VPS
  - `ufw allow from IP_DA_VPS to any port 5440`

**C. No Dokploy - Configurar rede:**
- Verifique se o container tem acesso à rede externa
- No Dokploy, verifique configurações de rede do projeto

#### 2. PostgreSQL na mesma VPS
Se o PostgreSQL está na mesma VPS, você pode estar usando o IP errado:
- Se PostgreSQL está em container Docker: use o **nome do serviço** ou **IP do container**
- Se PostgreSQL está rodando diretamente na VPS: use `host.docker.internal` ou configure `network_mode: host`

#### 3. Debug rápido
Para diagnosticar rapidamente:

```bash
# 1. Verificar se o container consegue resolver DNS
docker exec -it nome_container ping -c 2 31.97.22.234

# 2. Verificar se consegue conectar à porta
docker exec -it nome_container nc -zv 31.97.22.234 5440

# 3. Testar conexão Python diretamente
docker exec -it nome_container python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='31.97.22.234',
        port=5440,
        user='gestor_siscomex',
        password='H9#mZ8kP27vR58qX',
        database='siscomex_export_db',
        connect_timeout=5
    )
    print('OK: Conectado!')
    conn.close()
except Exception as e:
    print(f'ERRO: {e}')
"
```

### Como descobrir a configuração correta (PostgreSQL criado como Database no Dokploy) ⭐

**Se você criou o PostgreSQL como Database no Dokploy:**

1. **No Dokploy:**
   - Vá para a página do seu Database PostgreSQL
   - Procure por **"Connection Info"**, **"Internal URL"** ou **"Service Details"**
   - O Dokploy geralmente mostra:
     - **Host/Service Name**: Nome do serviço (ex: `postgres-abc123` ou `pg-xxx`)
     - **Port**: Geralmente `5432`
     - **User**: Geralmente `postgres` ou o que você configurou
     - **Password**: A senha que você definiu ou que o Dokploy gerou
     - **Database**: Nome do database

2. **Configurar variáveis no seu aplicativo:**
   ```
   POSTGRES_HOST=nome_do_servico  # Ex: postgres-abc123 ou pg-xxx (do passo 1)
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres  # ou o user do passo 1
   POSTGRES_PASSWORD=senha_do_database  # do passo 1
   POSTGRES_DB=nome_do_database  # do passo 1
   ```

3. **Linkar Database (se disponível):**
   - No seu projeto, vá em **"Settings"** → **"Link Database"**
   - Selecione seu database PostgreSQL
   - O Dokploy pode criar variáveis automaticamente (ex: `DATABASE_URL`)

**Se PostgreSQL está em container Docker manual:**
```bash
docker ps | grep postgres
docker inspect nome_container_postgres | grep IPAddress
```

**Se PostgreSQL está rodando diretamente na VPS:**
- Use `host.docker.internal` como `POSTGRES_HOST`

### Erro: "connection to server on socket ... failed: No such file or directory"
- **Variáveis não configuradas**: O sistema está tentando conectar via socket local
- Verifique se `POSTGRES_HOST` está configurado no Dokploy
- Verifique se todas as variáveis PostgreSQL estão configuradas
- Faça redeploy após configurar as variáveis

### Erro de conexão PostgreSQL
- Verifique as credenciais no Dokploy (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
- Verifique se o PostgreSQL está acessível da VPS (firewall/rede)
- Teste a conexão: `docker exec -it controle-siscomex python3 -c "from db_manager import db_manager; db_manager.conectar()"`
- Verifique logs: `docker exec -it controle-siscomex env | grep POSTGRES`

### Sincronização não executa
- Verifique se o cron está rodando: `docker exec -it controle-siscomex ps aux | grep cron`
- Verifique os logs do cron: `docker exec -it controle-siscomex tail -f /app/logs/cron.log`
- Verifique o timezone: `docker exec -it controle-siscomex date`
- Verifique se o arquivo cron_job.sh está correto: `docker exec -it controle-siscomex cat /etc/cron.d/cron_job`

### Erro de conexão AWS Athena
- Verifique as credenciais AWS no Dokploy (AWS_ACCESS_KEY, AWS_SECRET_KEY)
- Verifique se as credenciais têm permissão para usar Athena
- Verifique a região configurada (AWS_REGION)
- Verifique logs: `docker exec -it controle-siscomex env | grep AWS`

## Manutenção

### Atualizar código
1. Faça push das alterações para o repositório
2. No Dokploy, clique em "Redeploy"
3. Monitore os logs

### Atualizar dependências
1. Atualize o `requirements.txt`
2. Faça commit e push
3. No Dokploy, faça rebuild e redeploy

### Backup
- Configure backup do PostgreSQL
- Os dados são salvos apenas no PostgreSQL (não há arquivos locais)
