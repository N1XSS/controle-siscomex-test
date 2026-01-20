-- =============================================================================
-- MIGRATION 001: Remover campos que não existem na API Siscomex
-- =============================================================================
-- Data: 2026-01-20
-- Autor: Análise automática do schema vs API Siscomex
-- Motivo: API do Portal Único Siscomex não retorna estes campos
-- Impacto: NENHUM - Estes campos nunca foram populados pela API
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. TABELA: due_eventos_historico
-- -----------------------------------------------------------------------------
-- Remover 4 campos que não existem na resposta da API
-- API retorna apenas: dataEHoraDoEvento, evento, responsavel, informacoesAdicionais

ALTER TABLE due_eventos_historico
    DROP COLUMN IF EXISTS detalhes,
    DROP COLUMN IF EXISTS motivo,
    DROP COLUMN IF EXISTS tipo_evento,
    DROP COLUMN IF EXISTS data;

-- Adicionar comentário documentando a estrutura atual
COMMENT ON TABLE due_eventos_historico IS
    'Histórico de eventos da DUE. Campos detalhes, motivo, tipo_evento e data foram removidos em 2026-01-20 pois não existem na API Siscomex. API retorna apenas: dataEHoraDoEvento, evento, responsavel, informacoesAdicionais (opcional).';

-- -----------------------------------------------------------------------------
-- 2. TABELA: due_itens
-- -----------------------------------------------------------------------------
-- Remover campo exportador_nome que não existe na resposta da API
-- API retorna apenas: exportador.numeroDoDocumento, exportador.tipoDoDocumento,
-- exportador.estrangeiro, exportador.nacionalidade

ALTER TABLE due_itens
    DROP COLUMN IF EXISTS exportador_nome;

-- Adicionar comentário documentando a remoção
COMMENT ON TABLE due_itens IS
    'Itens da DUE. Campo exportador_nome foi removido em 2026-01-20 pois a API Siscomex retorna apenas numeroDoDocumento e tipoDoDocumento. Para obter o nome do exportador, consulte a API da Receita Federal usando o CNPJ/CPF.';

COMMENT ON COLUMN due_itens.exportador_numero_do_documento IS
    'Número do documento do exportador (CNPJ ou CPF). Para obter o nome da empresa/pessoa, consulte a API da Receita Federal.';

-- -----------------------------------------------------------------------------
-- 3. VERIFICAÇÃO FINAL
-- -----------------------------------------------------------------------------
-- Confirmar que as colunas foram removidas com sucesso

DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Verificar due_eventos_historico
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name = 'due_eventos_historico'
    AND column_name IN ('detalhes', 'motivo', 'tipo_evento', 'data');

    IF v_count > 0 THEN
        RAISE EXCEPTION 'ERRO: Ainda existem % colunas não removidas em due_eventos_historico', v_count;
    ELSE
        RAISE NOTICE 'OK: Todas as colunas removidas de due_eventos_historico';
    END IF;

    -- Verificar due_itens
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name = 'due_itens'
    AND column_name = 'exportador_nome';

    IF v_count > 0 THEN
        RAISE EXCEPTION 'ERRO: Coluna exportador_nome ainda existe em due_itens';
    ELSE
        RAISE NOTICE 'OK: Coluna exportador_nome removida de due_itens';
    END IF;
END $$;

COMMIT;

-- =============================================================================
-- FIM DA MIGRATION 001
-- =============================================================================

-- Para reverter esta migration (ROLLBACK):
--
-- BEGIN;
--
-- ALTER TABLE due_eventos_historico
--     ADD COLUMN IF NOT EXISTS detalhes VARCHAR(400),
--     ADD COLUMN IF NOT EXISTS motivo VARCHAR(150),
--     ADD COLUMN IF NOT EXISTS tipo_evento VARCHAR(50),
--     ADD COLUMN IF NOT EXISTS data TIMESTAMP;
--
-- ALTER TABLE due_itens
--     ADD COLUMN IF NOT EXISTS exportador_nome VARCHAR(150);
--
-- COMMIT;
--
-- NOTA: Estes campos permanecerão vazios pois a API não os retorna.
