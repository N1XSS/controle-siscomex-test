@echo off
REM =============================================================================
REM SYNC DIARIO - Sistema DUE Siscomex
REM =============================================================================
REM Este script realiza a sincronizacao completa diaria das DUEs.
REM Sugestao: Agendar via Agendador de Tarefas do Windows para executar 1x ao dia
REM
REM Instrucoes para agendamento:
REM 1. Abrir Agendador de Tarefas (taskschd.msc)
REM 2. Criar Tarefa Basica
REM 3. Nome: "DUE - Sync Diario"
REM 4. Disparador: Diariamente as 06:00
REM 5. Acao: Iniciar Programa - selecionar este arquivo .bat
REM =============================================================================

setlocal

REM Diretorio do projeto
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

REM Python (ajustar se necessario)
set "PYTHON=python"

REM Data e hora de inicio
echo ==============================================
echo SYNC DIARIO - %date% %time%
echo ==============================================

REM Verificar Python
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    exit /b 1
)

REM 1. Sincronizar novas NFs do SAP e buscar DUEs
echo.
echo [FASE 1] Sincronizando novas NFs...
echo ----------------------------------------------
%PYTHON% -m src.api.athena.client
%PYTHON% -m src.sync.new_dues

REM 2. Atualizar DUEs existentes
echo.
echo [FASE 2] Atualizando DUEs existentes...
echo ----------------------------------------------
%PYTHON% -m src.sync.update_dues

REM Resumo
echo.
echo ==============================================
echo SYNC CONCLUIDO - %date% %time%
echo ==============================================

endlocal
exit /b 0
