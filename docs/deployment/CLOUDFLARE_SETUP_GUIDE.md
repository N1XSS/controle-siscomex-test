# Guia de Configuração Cloudflare - agrovex.com.br

**Data**: 2026-01-20  
**Domínio**: agrovex.com.br  
**Status**: Em Configuração 🔄

---

## ✅ Passo 1: Nameservers (CONCLUÍDO)

### Alteração Realizada

**Nameservers Antigos (Hostinger):**
- ❌ ns1.dns-parking.com
- ❌ ns2.dns-parking.com

**Nameservers Novos (Cloudflare):**
- ✅ magali.ns.cloudflare.com
- ✅ remy.ns.cloudflare.com

**Status**: Alteração solicitada com sucesso na Hostinger  
**Tempo de Propagação**: 24-48 horas (geralmente 2-4 horas)

---

## 🔒 Passo 2: Desabilitar DNSSEC

### O que é DNSSEC?
DNSSEC (Domain Name System Security Extensions) adiciona assinatura criptográfica aos registros DNS. Precisa ser desabilitado durante a migração para Cloudflare.

### Como Desabilitar na Hostinger:

1. **Acesse**: https://hpanel.hostinger.com/domain/agrovex.com.br/dns
2. **Procure**: Seção "DNSSEC" ou "Segurança DNS"
3. **Desabilite**: Se estiver ativado, clique em "Desabilitar" ou "Disable"
4. **Salve**: Confirme as alterações

### Verificar se DNSSEC está ativo:

```bash
# No terminal/PowerShell
dig +dnssec agrovex.com.br

# Ou online em: https://dnssec-analyzer.verisignlabs.com/
```

**⚠️ IMPORTANTE**: Após a migração para Cloudflare estar completa, você pode reabilitar o DNSSEC através do painel da Cloudflare.

---

## 🔥 Passo 3: Configurar Firewall da VPS (Opcional mas Recomendado)

### Por que fazer isso?
Permite apenas tráfego originado da Cloudflare, protegendo sua VPS de ataques diretos ao IP.

### IPs da Cloudflare a Permitir:

#### IPv4:
```
173.245.48.0/20
103.21.244.0/22
103.22.200.0/22
103.31.4.0/22
141.101.64.0/18
108.162.192.0/18
190.93.240.0/20
188.114.96.0/20
197.234.240.0/22
198.41.128.0/17
162.158.0.0/15
104.16.0.0/13
104.24.0.0/14
172.64.0.0/13
131.0.72.0/22
```

#### IPv6:
```
2400:cb00::/32
2606:4700::/32
2803:f800::/32
2405:b500::/32
2405:8100::/32
2a06:98c0::/29
2c0f:f248::/32
```

### Comandos para Configurar UFW (Ubuntu/Debian):

```bash
# Conectar na VPS
ssh root@31.97.22.234

# Backup das regras atuais
sudo ufw status numbered > /root/ufw_backup_$(date +%Y%m%d).txt

# Permitir SSH (IMPORTANTE - fazer PRIMEIRO)
sudo ufw allow 22/tcp

# Remover regras antigas de HTTP/HTTPS se existirem
sudo ufw delete allow 80/tcp
sudo ufw delete allow 443/tcp

# Script para adicionar IPs da Cloudflare
cat > /tmp/cloudflare_ufw.sh << 'EOF'
#!/bin/bash
# IPs IPv4 da Cloudflare
for ip in \
  173.245.48.0/20 \
  103.21.244.0/22 \
  103.22.200.0/22 \
  103.31.4.0/22 \
  141.101.64.0/18 \
  108.162.192.0/18 \
  190.93.240.0/20 \
  188.114.96.0/20 \
  197.234.240.0/22 \
  198.41.128.0/17 \
  162.158.0.0/15 \
  104.16.0.0/13 \
  104.24.0.0/14 \
  172.64.0.0/13 \
  131.0.72.0/22
do
  sudo ufw allow from $ip to any port 80 proto tcp
  sudo ufw allow from $ip to any port 443 proto tcp
done

# IPs IPv6 da Cloudflare
for ip in \
  2400:cb00::/32 \
  2606:4700::/32 \
  2803:f800::/32 \
  2405:b500::/32 \
  2405:8100::/32 \
  2a06:98c0::/29 \
  2c0f:f248::/32
do
  sudo ufw allow from $ip to any port 80 proto tcp
  sudo ufw allow from $ip to any port 443 proto tcp
done

echo "Regras da Cloudflare adicionadas com sucesso!"
EOF

# Executar script
chmod +x /tmp/cloudflare_ufw.sh
sudo /tmp/cloudflare_ufw.sh

# Habilitar firewall (se ainda não estiver)
sudo ufw enable

# Verificar regras
sudo ufw status numbered
```

### ⚠️ ATENÇÃO:
- **NÃO bloqueie a porta 22 (SSH)** - você pode perder acesso à VPS
- **Teste antes de aplicar** em produção
- **Mantenha uma sessão SSH aberta** enquanto testa

---

## 📊 Passo 4: Importar Registros DNS no Cloudflare

### Registros DNS a Adicionar no Cloudflare:

Todos os registros abaixo devem ser adicionados como **Proxied (Nuvem Laranja)** para proteção:

#### Registro Principal:
```
Tipo: A
Nome: @
Conteúdo: 84.32.84.32
Proxy: ON (Laranja)
TTL: Auto
```

#### Subdomínios VPS (31.97.22.234):
```
Tipo: A | Nome: panel          | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: n8n            | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: evolution      | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: metabase       | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: brycloud       | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: brycloud-admin | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: adminer        | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: minio          | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: whatsapp       | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: cockpit        | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: llm            | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: comfyui        | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: hvi            | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: pdf-generator  | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: apps           | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: due            | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: db-siscomex    | IP: 31.97.22.234 | Proxy: ON
Tipo: A | Nome: brycloud-webhook | IP: 31.97.22.234 | Proxy: ON
```

#### CNAME:
```
Tipo: CNAME
Nome: www
Conteúdo: agrovex.com.br
Proxy: ON (Laranja)
TTL: Auto
```

**💡 Dica**: A Cloudflare geralmente importa os registros automaticamente quando você adiciona o domínio. Verifique se todos estão corretos!

---

## 🔐 Passo 5: Configurar SSL/TLS no Cloudflare

### Configurações Recomendadas:

1. **SSL/TLS Encryption Mode**: Full (Strict)
   - Caminho: SSL/TLS → Overview
   - Selecione: **Full (strict)**

2. **Always Use HTTPS**: ON
   - Caminho: SSL/TLS → Edge Certificates
   - Ative: **Always Use HTTPS**

3. **Automatic HTTPS Rewrites**: ON
   - Caminho: SSL/TLS → Edge Certificates
   - Ative: **Automatic HTTPS Rewrites**

4. **Minimum TLS Version**: TLS 1.2
   - Caminho: SSL/TLS → Edge Certificates
   - Selecione: **TLS 1.2**

5. **Opportunistic Encryption**: ON
   - Caminho: SSL/TLS → Edge Certificates
   - Ative: **Opportunistic Encryption**

---

## ⚡ Passo 6: Otimizações Performance (Opcional)

### Speed → Optimization

1. **Auto Minify**: 
   - JavaScript: ON
   - CSS: ON
   - HTML: ON

2. **Brotli**: ON

3. **Rocket Loader**: ON (teste - pode quebrar alguns sites)

### Caching

1. **Caching Level**: Standard

2. **Browser Cache TTL**: 4 hours

---

## 🛡️ Passo 7: Segurança Adicional (Opcional)

### Firewall Rules

Criar regra para bloquear bots ruins:

```
(cf.client.bot) and not (cf.verified_bot_category in {"Search Engine Crawler"})
Action: Block
```

### Security Level

- Recomendado: **Medium**
- Ajuste conforme necessário

---

## ✅ Checklist de Verificação

Após a propagação dos nameservers (2-48 horas):

- [ ] Nameservers propagados (verificar em: https://dnschecker.org/)
- [ ] DNSSEC desabilitado na Hostinger
- [ ] Todos os registros DNS importados no Cloudflare
- [ ] SSL/TLS configurado como Full (Strict)
- [ ] Testar acesso a todos os subdomínios
- [ ] Firewall da VPS configurado (opcional)
- [ ] Habilitar DNSSEC no Cloudflare (após tudo estabilizar)

---

## 🧪 Testar Conexão após Propagação

```bash
# Verificar nameservers
nslookup agrovex.com.br

# Verificar resolução DNS
ping panel.agrovex.com.br
ping n8n.agrovex.com.br

# Verificar SSL
curl -I https://panel.agrovex.com.br
curl -I https://n8n.agrovex.com.br
```

---

## 📞 Suporte

### Cloudflare:
- Documentação: https://developers.cloudflare.com/
- Status: https://www.cloudflarestatus.com/
- Community: https://community.cloudflare.com/

### Hostinger:
- Support: https://hpanel.hostinger.com/
- Live Chat: Disponível no painel

---

## 🚨 Troubleshooting

### Erro "Too Many Redirects"
- **Causa**: SSL/TLS no Cloudflare está em "Flexible" mas o servidor força HTTPS
- **Solução**: Mudar para "Full" ou "Full (Strict)"

### Site não carrega após mudança
- **Causa**: Nameservers ainda não propagaram
- **Solução**: Aguardar até 48h, verificar em dnschecker.org

### Alguns serviços não funcionam
- **Causa**: Registros DNS não foram importados corretamente
- **Solução**: Adicionar manualmente no Cloudflare

---

## 📝 Notas Importantes

1. **Não desabilite o proxy (nuvem laranja)** nos registros, a menos que necessário
2. **Mantenha backup** das configurações DNS antigas
3. **Teste gradualmente** - não faça todas as mudanças de uma vez
4. **Monitore logs** da VPS após ativar firewall Cloudflare
5. **SSL/TLS Full (Strict)** requer certificado válido no servidor de origem

---

**Documento criado em**: 2026-01-20  
**Última atualização**: 2026-01-20  
**Status**: Em Migração 🔄
