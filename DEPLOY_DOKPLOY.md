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

```
POSTGRES_HOST=31.97.22.234
POSTGRES_PORT=5440
POSTGRES_USER=gestor_siscomex
POSTGRES_PASSWORD=sua_senha_aqui
POSTGRES_DB=siscomex_export_db
```

**⚠️ ATENÇÃO**: Se estiver usando PostgreSQL externo (como no exemplo acima), certifique-se de que:
- O firewall permite conexões da VPS (IP da VPS)
- O PostgreSQL está configurado para aceitar conexões remotas
- A porta está aberta (5440 no exemplo)

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
- Verifique se todas as variáveis de ambiente estão configuradas
- Verifique a conexão com PostgreSQL

### Sincronização não executa
- Verifique se o cron está rodando: `docker exec -it controle-siscomex ps aux | grep cron`
- Verifique os logs do cron: `docker exec -it controle-siscomex tail -f /app/logs/cron.log`
- Verifique o timezone: `docker exec -it controle-siscomex date`

### Erro de conexão PostgreSQL
- Verifique as credenciais no Dokploy
- Verifique se o PostgreSQL está acessível da VPS
- Teste a conexão: `docker exec -it controle-siscomex python3 -c "from db_manager import db_manager; db_manager.conectar()"`

### Erro de conexão AWS Athena
- Verifique as credenciais AWS no Dokploy
- Verifique se as credenciais têm permissão para usar Athena
- Verifique a região configurada

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
