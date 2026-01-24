# Configurações DNS - agrovex.com.br

**Data de Exportação**: 2026-01-20  
**Domínio**: agrovex.com.br  
**Servidor DNS**: Hostinger

---

## 📋 Registros DNS Configurados

### Registro Principal (@)

| Tipo | Nome | Conteúdo | TTL | Status |
|------|------|----------|-----|--------|
| A | @ | 84.32.84.32 | 50 | ✅ Ativo |

### Registros CAA (Certificate Authority Authorization)

| Tipo | Nome | Conteúdo | TTL | Status |
|------|------|----------|-----|--------|
| CAA | @ | 0 issue "letsencrypt.org" | 14400 | ✅ Ativo |
| CAA | @ | 0 issue "digicert.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issue "sectigo.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issue "comodoca.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issue "globalsign.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issue "pki.goog" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "letsencrypt.org" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "digicert.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "sectigo.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "comodoca.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "globalsign.com" | 14400 | ✅ Ativo |
| CAA | @ | 0 issuewild "pki.goog" | 14400 | ✅ Ativo |

---

## 🖥️ Subdomínios VPS (IP: 31.97.22.234)

Todos os seguintes subdomínios apontam para a VPS no IP **31.97.22.234**:

### Gestão e Administração

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | panel | 31.97.22.234 | 300 | ✅ Ativo | Painel Dokploy |
| A | cockpit | 31.97.22.234 | 300 | ✅ Ativo | Cockpit Server |
| A | adminer | 31.97.22.234 | 300 | ✅ Ativo | Adminer DB |

### Automação e Integração

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | n8n | 31.97.22.234 | 300 | ✅ Ativo | Automação n8n |
| A | evolution | 31.97.22.234 | 300 | ✅ Ativo | Evolution API |
| A | whatsapp | 31.97.22.234 | 300 | ✅ Ativo | WhatsApp API |

### Aplicações e Serviços

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | apps | 31.97.22.234 | 300 | ✅ Ativo | Aplicações Gerais |
| A | brycloud | 31.97.22.234 | 300 | ✅ Ativo | BryCloud Main |
| A | brycloud-admin | 31.97.22.234 | 300 | ✅ Ativo | BryCloud Admin |
| A | brycloud-webhook | 31.97.22.234 | 300 | ✅ Ativo | BryCloud Webhooks |
| A | metabase | 31.97.22.234 | 300 | ✅ Ativo | Metabase BI |
| A | due | 31.97.22.234 | 300 | ✅ Ativo | Sistema DUE |

### Inteligência Artificial

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | llm | 31.97.22.234 | 300 | ✅ Ativo | LLM/IA Services |
| A | comfyui | 31.97.22.234 | 300 | ✅ Ativo | ComfyUI |
| A | hvi | 31.97.22.234 | 300 | ✅ Ativo | HVI |

### Utilitários e Ferramentas

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | minio | 31.97.22.234 | 300 | ✅ Ativo | MinIO Storage |
| A | pdf-generator | 31.97.22.234 | 300 | ✅ Ativo | PDF Generator |

### Banco de Dados

| Tipo | Subdomínio | IP | TTL | Status | Função |
|------|------------|-----|-----|--------|--------|
| A | db-siscomex | 31.97.22.234 | 14400 | ✅ Ativo | Database Siscomex |

---

## 🌐 Outros Registros

| Tipo | Nome | Conteúdo | TTL | Status |
|------|------|----------|-----|--------|
| CNAME | www | agrovex.com.br. | 300 | ✅ Ativo |

---

## 📊 Estatísticas

- **Total de Registros A**: 19
- **Total de Registros CAA**: 12
- **Total de Registros CNAME**: 1
- **IP Principal VPS**: 31.97.22.234
- **TTL Médio**: 300 segundos (5 minutos)

---

## 🔒 Certificados SSL Autorizados

Os registros CAA autorizam certificados SSL das seguintes autoridades:

1. **Let's Encrypt** (letsencrypt.org) - Usado pelo Traefik/Dokploy
2. **DigiCert** (digicert.com)
3. **Sectigo** (sectigo.com)
4. **Comodo** (comodoca.com)
5. **GlobalSign** (globalsign.com)
6. **Google Trust Services** (pki.goog)

---

## ✅ Status Geral dos Serviços

### Serviços Testados e Funcionando:

- ✅ **n8n.agrovex.com.br** - Funcionando com SSL
- ✅ **metabase.agrovex.com.br** - Funcionando com SSL
- ✅ **brycloud.agrovex.com.br** - Funcionando com SSL
- ✅ **evolution.agrovex.com.br** - Funcionando com SSL

### Serviços que Precisam de Configuração:

- ⚠️ **panel.agrovex.com.br** - Requer porta :3000 (necessita configuração no Dokploy)

---

## 🔧 Observações Técnicas

1. **Traefik está funcionando** - O reverse proxy está ativo e gerenciando SSL automaticamente
2. **DNS está correto** - Todos os registros apontam para o IP correto
3. **SSL automático** - Certificados Let's Encrypt sendo emitidos automaticamente
4. **TTL baixo** - TTL de 300s permite mudanças rápidas de configuração

---

## 📝 Recomendações

1. Configurar o domínio do painel Dokploy em Settings → Server
2. Habilitar SSL para o painel
3. Documentar qual aplicação está em cada subdomínio
4. Considerar aumentar TTL para 3600s (1 hora) após estabilização

---

**Documento gerado automaticamente em**: 2026-01-20  
**Última atualização**: 2026-01-20  
**Responsável**: Sistema de Automação
