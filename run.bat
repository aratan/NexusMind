@echo off
title Inicialización SaaS

echo ==========================================
echo Iniciando scripts de forma asíncrona...
echo ==========================================

REM NOTA: El comando 'start' abre una nueva ventana.
REM /k significa "Keep" (mantiene la ventana abierta para ver la salida).
REM Si prefieres que no aparezcan ventanas nuevas, usa python script.py en su lugar.

REM --- Script 1: Aplicación Principal ---
REM Usamos "start" para lanzar el proceso de forma independiente
start "Titulo_Ventana_SaaS" cmd /k python saasweb.py

sleep 2

REM --- Script 2: Trabajador (Worker) ---
start "Titulo_Ventana_Worker" cmd /k python worker.py

sleep 2 

REM --- Script 3: Cliente ---
REM Asumiendo que el archivo correcto es client.py (corregiendo el typo .pt)
start "Titulo_Ventana_Client" cmd /k python client.py



echo ==========================================
echo Todos los scripts se han iniciado.
echo Para cerrar las ventanas, cierra los iconos en la barra de tareas.
echo ==========================================
