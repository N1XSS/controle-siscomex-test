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

#### 2. PostgreSQL rodando diretamente na VPS (não containerizado)

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
- **PostgreSQL na mesma VPS**: Se o PostgreSQL está na mesma VPS, você pode estar usando o IP errado
  - Se PostgreSQL está em container Docker: use o **nome do serviço** ou **IP do container**
  - Se PostgreSQL está rodando diretamente na VPS: use `host.docker.internal` ou configure `network_mode: host`
- **PostgreSQL externo**: Verifique se o firewall permite conexões
- Verifique se o PostgreSQL aceita conexões remotas (postgresql.conf: `listen_addresses = '*'`)
- Verifique se o pg_hba.conf permite conexões
- Teste conectividade: `docker exec -it controle-siscomex nc -zv IP_POSTGRES PORTA`

### Como descobrir a configuração correta (PostgreSQL na mesma VPS)

**1. Verificar se PostgreSQL está em container Docker:**
```bash
docker ps | grep postgres
```
Se retornar um container, note o nome e use como `POSTGRES_HOST`

**2. Se PostgreSQL está em container, descobrir IP:**
```bash
docker inspect nome_container_postgres | grep IPAddress
```
Use esse IP como `POSTGRES_HOST`

**3. Se PostgreSQL está rodando diretamente na VPS:**
- Use `host.docker.internal` como `POSTGRES_HOST`
- Ou configure o container no Dokploy para usar `network_mode: host` (então use `localhost`)

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
