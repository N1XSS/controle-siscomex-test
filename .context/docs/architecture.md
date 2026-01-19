---
status: unfilled
generated: 2026-01-17
---

# Architecture Notes

Describe how the system is assembled and why the current design exists.

## System Architecture Overview

Summarize the top-level topology (monolith, modular service, microservices) and deployment model. Highlight how requests traverse the system and where control pivots between layers.

## Architectural Layers
- *No architectural layers detected.*

## Detected Design Patterns
- *No design patterns detected yet.*

## Entry Points
- *No entry points detected.*

## Public API
| Symbol | Type | Location |
| --- | --- | --- |
| [`atualizar_drawback`](main.py#L239) | function | main.py:239 |
| [`atualizar_due_especifica`](main.py#L119) | function | main.py:119 |
| [`atualizar_dues`](sync_atualizar.py#L459) | function | sync_atualizar.py:459 |
| [`atualizar_existentes`](main.py#L402) | function | main.py:402 |
| [`baixar_tabelas_suporte`](download_tabelas.py#L311) | function | download_tabelas.py:311 |
| [`carregar_cache_due_siscomex`](due_processor.py#L1046) | function | due_processor.py:1046 |
| [`carregar_dues_para_verificar`](sync_atualizar.py#L77) | function | sync_atualizar.py:77 |
| [`carregar_nfs_sap`](sync_novas.py#L46) | function | sync_novas.py:46 |
| [`carregar_vinculos_existentes`](sync_novas.py#L87) | function | sync_novas.py:87 |
| [`consultar_dados_adicionais`](sync_novas.py#L156) | function | sync_novas.py:156 |
| [`consultar_dados_adicionais`](sync_atualizar.py#L244) | function | sync_atualizar.py:244 |
| [`consultar_dados_tabela`](download_tabelas.py#L104) | function | download_tabelas.py:104 |
| [`consultar_due_completa`](due_processor.py#L579) | function | due_processor.py:579 |
| [`consultar_due_por_nf`](due_processor.py#L643) | function | due_processor.py:643 |
| [`consultar_due_por_numero`](due_processor.py#L815) | function | due_processor.py:815 |
| [`consultar_metadados_tabela`](download_tabelas.py#L63) | function | download_tabelas.py:63 |
| [`consultar_nfs_exportacao`](consulta_sap.py#L240) | function | consulta_sap.py:240 |
| [`criar_cliente_athena`](consulta_sap.py#L117) | function | consulta_sap.py:117 |
| [`criar_estrutura_diretorios`](instalar.py#L34) | function | instalar.py:34 |
| [`criar_resumo_tabelas_suporte`](download_tabelas.py#L281) | function | download_tabelas.py:281 |
| [`DatabaseManager`](db_manager.py#L54) | class | db_manager.py:54 |
| [`executar_query_athena`](consulta_sap.py#L142) | function | consulta_sap.py:142 |
| [`executar_script`](main.py#L85) | function | main.py:85 |
| [`exibir_cabecalho`](main.py#L38) | function | main.py:38 |
| [`exibir_status`](main.py#L48) | function | main.py:48 |
| [`gerar_script_agendamento`](main.py#L434) | function | main.py:434 |
| [`instalar_dependencias`](instalar.py#L22) | function | instalar.py:22 |
| [`ler_chaves_nf`](due_processor.py#L26) | function | due_processor.py:26 |
| [`listar_tabelas_disponivel`](download_tabelas.py#L22) | function | download_tabelas.py:22 |
| [`main`](sync_novas.py#L371) | function | sync_novas.py:371 |
| [`main`](sync_atualizar.py#L700) | function | sync_atualizar.py:700 |
| [`main`](main.py#L577) | function | main.py:577 |
| [`main`](instalar.py#L139) | function | instalar.py:139 |
| [`main`](due_processor.py#L1495) | function | due_processor.py:1495 |
| [`main`](download_tabelas.py#L452) | function | download_tabelas.py:452 |
| [`main`](consulta_sap.py#L330) | function | consulta_sap.py:330 |
| [`menu_interativo`](main.py#L541) | function | main.py:541 |
| [`mostrar_proximos_passos`](instalar.py#L100) | function | instalar.py:100 |
| [`normalizar_dados_tabela`](download_tabelas.py#L194) | function | download_tabelas.py:194 |
| [`processar_chave_individual`](due_processor.py#L931) | function | due_processor.py:931 |
| [`processar_chaves_nf`](due_processor.py#L1073) | function | due_processor.py:1073 |
| [`processar_dados_due`](due_processor.py#L52) | function | due_processor.py:52 |
| [`processar_due_averbada_antiga`](sync_atualizar.py#L280) | function | sync_atualizar.py:280 |
| [`processar_dues_averbadas_antigas_paralelo`](sync_atualizar.py#L339) | function | sync_atualizar.py:339 |
| [`processar_novas_nfs`](sync_novas.py#L192) | function | sync_novas.py:192 |
| [`processar_sequencial_simples`](due_processor.py#L1280) | function | due_processor.py:1280 |
| [`processar_tabela_individual`](download_tabelas.py#L161) | function | download_tabelas.py:161 |
| [`salvar_nfs`](consulta_sap.py#L296) | function | consulta_sap.py:296 |
| [`salvar_novos_vinculos`](sync_novas.py#L107) | function | sync_novas.py:107 |
| [`salvar_resultados`](due_processor.py#L1436) | function | due_processor.py:1436 |
| [`salvar_resultados_normalizados`](due_processor.py#L1314) | function | due_processor.py:1314 |
| [`salvar_tabelas_suporte`](download_tabelas.py#L251) | function | download_tabelas.py:251 |
| [`SharedTokenManager`](token_manager.py#L26) | class | token_manager.py:26 |
| [`sincronizacao_completa`](main.py#L418) | function | main.py:418 |
| [`sincronizar_novas`](main.py#L99) | function | main.py:99 |
| [`testar_instalacao`](instalar.py#L77) | function | instalar.py:77 |
| [`testar_normalizacao_due`](due_processor.py#L1459) | function | due_processor.py:1459 |
| [`verificar_arquivo_env`](instalar.py#L51) | function | instalar.py:51 |
| [`verificar_python`](instalar.py#L12) | function | instalar.py:12 |
| [`verificar_se_due_mudou`](sync_atualizar.py#L182) | function | sync_atualizar.py:182 |

## Internal System Boundaries

Document seams between domains, bounded contexts, or service ownership. Note data ownership, synchronization strategies, and shared contract enforcement.

## External Service Dependencies

List SaaS platforms, third-party APIs, or infrastructure services the system relies on. Describe authentication methods, rate limits, and failure considerations for each dependency.

## Key Decisions & Trade-offs

Summarize architectural decisions, experiments, or ADR outcomes that shape the current design. Reference supporting documents and explain why selected approaches won over alternatives.

## Diagrams

Link architectural diagrams or add mermaid definitions here.

## Risks & Constraints

Document performance constraints, scaling considerations, or external system assumptions.

## Top Directories Snapshot
- `__pycache__/` — approximately 11 files
- `config_exemplo.env/` — approximately 1 files
- `config.env/` — approximately 1 files
- `consulta_sap.py/` — approximately 1 files
- `cron_job.sh/` — approximately 1 files
- `dados/` — approximately 0 files
- `db_manager.py/` — approximately 1 files
- `db_schema.py/` — approximately 1 files
- `DEPLOY_DOKPLOY.md/` — approximately 1 files
- `docker-compose.yml/` — approximately 1 files
- `Dockerfile/` — approximately 1 files
- `docs/` — approximately 6 files
- `download_tabelas.py/` — approximately 1 files
- `due_processor.py/` — approximately 1 files
- `entrypoint.sh/` — approximately 1 files
- `instalar.py/` — approximately 1 files
- `LICENSE/` — approximately 1 files
- `main.py/` — approximately 1 files
- `README.md/` — approximately 1 files
- `requirements.txt/` — approximately 1 files
- `scripts/` — approximately 2 files
- `sync_atualizar.py/` — approximately 1 files
- `sync_novas.py/` — approximately 1 files
- `test_connection.sh/` — approximately 1 files
- `token_cache.pkl/` — approximately 1 files
- `token_manager.py/` — approximately 1 files
- `TUTORIAL_TESTES_VPS.md/` — approximately 1 files

## Related Resources

- [Project Overview](./project-overview.md)
- Update [agents/README.md](../agents/README.md) when architecture changes.
