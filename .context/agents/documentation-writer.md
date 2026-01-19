---
name: Documentation Writer
description: Create clear, comprehensive documentation
status: unfilled
generated: 2026-01-17
---

# Documentation Writer Agent Playbook

## Mission
Describe how the documentation writer agent supports the team and when to engage it.

## Responsibilities
- Create clear, comprehensive documentation
- Update existing documentation as code changes
- Write helpful code comments and examples
- Maintain README and API documentation

## Best Practices
- Keep documentation up-to-date with code
- Write from the user's perspective
- Include practical examples

## Key Project Resources
- Documentation index: [docs/README.md](../docs/README.md)
- Agent handbook: [agents/README.md](./README.md)
- Agent knowledge base: [AGENTS.md](../../AGENTS.md)
- Contributor guide: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Repository Starting Points
- `__pycache__/` — TODO: Describe the purpose of this directory.
- `dados/` — TODO: Describe the purpose of this directory.
- `docs/` — TODO: Describe the purpose of this directory.
- `scripts/` — TODO: Describe the purpose of this directory.

## Key Files
- *No key files detected.*

## Key Symbols for This Agent
- [`SharedTokenManager`](token_manager.py#L26) (class)
- [`DatabaseManager`](db_manager.py#L54) (class)
- [`carregar_nfs_sap`](sync_novas.py#L46) (function)
- [`carregar_vinculos_existentes`](sync_novas.py#L87) (function)
- [`salvar_novos_vinculos`](sync_novas.py#L107) (function)
- [`consultar_dados_adicionais`](sync_novas.py#L156) (function)
- [`processar_novas_nfs`](sync_novas.py#L192) (function)
- [`main`](sync_novas.py#L371) (function)
- [`carregar_dues_para_verificar`](sync_atualizar.py#L77) (function)
- [`verificar_se_due_mudou`](sync_atualizar.py#L182) (function)
- [`consultar_dados_adicionais`](sync_atualizar.py#L244) (function)
- [`processar_due_averbada_antiga`](sync_atualizar.py#L280) (function)
- [`processar_dues_averbadas_antigas_paralelo`](sync_atualizar.py#L339) (function)
- [`atualizar_dues`](sync_atualizar.py#L459) (function)
- [`main`](sync_atualizar.py#L700) (function)

## Documentation Touchpoints
- [Documentation Index](../docs/README.md)
- [Project Overview](../docs/project-overview.md)
- [Architecture Notes](../docs/architecture.md)
- [Development Workflow](../docs/development-workflow.md)
- [Testing Strategy](../docs/testing-strategy.md)
- [Glossary & Domain Concepts](../docs/glossary.md)
- [Data Flow & Integrations](../docs/data-flow.md)
- [Security & Compliance Notes](../docs/security.md)
- [Tooling & Productivity Guide](../docs/tooling.md)

## Collaboration Checklist

1. Confirm assumptions with issue reporters or maintainers.
2. Review open pull requests affecting this area.
3. Update the relevant doc section listed above.
4. Capture learnings back in [docs/README.md](../docs/README.md).

## Hand-off Notes

Summarize outcomes, remaining risks, and suggested follow-up actions after the agent completes its work.
