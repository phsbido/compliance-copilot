@echo off
rem Atalho da interface web do copiloto (Camada 1): sobe o Ollama, se
rem ainda nao estiver rodando, e abre o chat no navegador.
rem Uso: dois cliques neste arquivo (ou no atalho da Area de Trabalho).
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist "venv\Scripts\python.exe" (
    echo Ambiente virtual nao encontrado em "%~dp0venv".
    echo Crie-o seguindo a secao "Instalacao" do README.
    goto erro
)

curl -s -m 2 http://localhost:11434/api/version >nul 2>&1
if not errorlevel 1 goto iniciar

set "OLLAMA_EXE=ollama"
where ollama >nul 2>&1
if errorlevel 1 set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not "%OLLAMA_EXE%"=="ollama" if not exist "%OLLAMA_EXE%" (
    echo Ollama nao encontrado. Instale em https://ollama.com/download
    goto erro
)

echo Iniciando o Ollama...
start "Ollama" /min "%OLLAMA_EXE%" serve
for /l %%i in (1,1,30) do (
    curl -s -m 2 http://localhost:11434/api/version >nul 2>&1
    if not errorlevel 1 goto iniciar
    ping -n 2 127.0.0.1 >nul
)
echo O Ollama nao respondeu em 30 segundos.
goto erro

:iniciar
"venv\Scripts\python.exe" main_web.py %*
if errorlevel 1 goto erro
exit /b 0

:erro
echo.
pause
exit /b 1
