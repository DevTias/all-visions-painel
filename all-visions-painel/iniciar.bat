@echo off
rem ALL VISIONS - painel da festa. De dois cliques para abrir.
cd /d "%~dp0"

set "PY="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"
if not defined PY (
  echo Python nao encontrado. Instale o Python 3.12 em https://www.python.org/downloads/ e rode de novo.
  pause
  exit /b 1
)

rem o ambiente fica fora do OneDrive para nao sincronizar milhares de arquivos
set "VENV=%LOCALAPPDATA%\all-visions-painel\venv"
if not exist "%VENV%\Scripts\python.exe" (
  echo Preparando o ambiente pela primeira vez...
  "%PY%" -m venv "%VENV%"
  "%VENV%\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
)

start "" http://127.0.0.1:5000
"%VENV%\Scripts\python.exe" app.py
pause
