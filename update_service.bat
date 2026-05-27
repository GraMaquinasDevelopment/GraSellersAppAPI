@echo off
REM ======================================================
REM Instala e configura o serviço GRASellersAppAPI com NSSM
REM ======================================================

REM Caminho do NSSM
SET NSSM_PATH=C:\nssm\win64\nssm.exe

REM Nome do serviço
SET SERVICE_NAME=GRASellersApp

REM Caminho do Python
SET PYTHON_PATH=C:\Users\Administrador\AppData\Local\Programs\Python\Python313\python.exe

REM Diretório do projeto
SET PROJECT_DIR=D:\GraSellersAppAPI

REM Caminho dos logs
SET LOG_STDOUT=%PROJECT_DIR%\logs\api_output.log
SET LOG_STDERR=%PROJECT_DIR%\logs\api_error.log

REM ===========================================
ECHO Removendo serviço antigo (caso exista)...
"%NSSM_PATH%" remove %SERVICE_NAME% confirm

REM ===========================================
ECHO Instalando novo serviço...
REM ------------------------------------------------------
REM Alteração: AppParameters movido para o comando de instalação
REM Motivo: NSSM pode receber diretamente os parâmetros do Python no mesmo comando
REM ------------------------------------------------------
"%NSSM_PATH%" install %SERVICE_NAME% "%PYTHON_PATH%" -m uvicorn main:app --host 0.0.0.0 --port 8081 --reload

REM Configurar diretório de trabalho
"%NSSM_PATH%" set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"

REM Configurar logs
"%NSSM_PATH%" set %SERVICE_NAME% AppStdout "%LOG_STDOUT%"
"%NSSM_PATH%" set %SERVICE_NAME% AppStderr "%LOG_STDERR%"
"%NSSM_PATH%" set %SERVICE_NAME% AppStdoutCreationDisposition 4
"%NSSM_PATH%" set %SERVICE_NAME% AppStderrCreationDisposition 4

REM Configurar restart automático
"%NSSM_PATH%" set %SERVICE_NAME% AppExit Default Restart
"%NSSM_PATH%" set %SERVICE_NAME% AppRestartDelay 5000

REM Iniciar automaticamente com o Windows
"%NSSM_PATH%" set %SERVICE_NAME% Start SERVICE_AUTO_START

REM ------------------------------------------------------
REM Alteração: Adicionado AppEnvironmentExtra PYTHONUTF8=1
REM Motivo: Força UTF-8 no serviço, resolvendo o erro com emojis
REM ------------------------------------------------------
"%NSSM_PATH%" set %SERVICE_NAME% AppEnvironmentExtra PYTHONUTF8=1

ECHO ======================================================
ECHO Serviço %SERVICE_NAME% instalado e configurado com sucesso!
ECHO Para iniciar: net start %SERVICE_NAME%
ECHO Para parar: net stop %SERVICE_NAME%
ECHO Logs de saída: %LOG_STDOUT%
ECHO Logs de erro: %LOG_STDERR%
ECHO ======================================================
PAUSE
