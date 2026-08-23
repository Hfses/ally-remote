@echo off
title Ally Remote — Instalador de Servico
color 0A

echo.
echo  =====================================================
echo   ALLY REMOTE — Instalador de Servico Windows
echo  =====================================================
echo.
echo  Este script vai:
echo    1. Instalar as dependencias necessarias
echo    2. Configurar PIN de seguranca
echo    3. Instalar o Ally Remote como servico do Windows
echo       (inicia automaticamente com o PC)
echo.
echo  ATENCAO: Execute como Administrador!
echo.

:: Verifica se é admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERRO: Execute este arquivo como Administrador.
    echo  Clique com o botao direito ^> "Executar como administrador"
    pause
    exit /b 1
)

:: Instala dependências
echo [1/3] Instalando dependencias Python...
pip install pywin32 fastapi uvicorn[standard] qrcode pillow pynput hidapi mss >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERRO: Falha ao instalar dependencias. Verifique se o Python esta instalado.
    pause
    exit /b 1
)
echo  OK

:: Configura
echo [2/3] Configurando...
python service_install.py config
if %errorlevel% neq 0 ( pause & exit /b 1 )

:: Instala serviço
echo [3/3] Instalando servico...
python service_install.py install
if %errorlevel% neq 0 ( pause & exit /b 1 )

echo.
echo  =====================================================
echo   Instalacao concluida!
echo   O Ally Remote agora inicia automaticamente com o PC.
echo.
echo   Para gerenciar:
echo     python service_install.py status   (ver status)
echo     python service_install.py stop     (parar)
echo     python service_install.py start    (iniciar)
echo     python service_install.py config   (alterar PIN/porta)
echo     python service_install.py remove   (desinstalar)
echo  =====================================================
echo.
pause
