# -*- coding: utf-8 -*-
import json, logging, asyncio, os, sys, re, hashlib
import aiohttp
# import shlex
from solders.keypair import Keypair

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WORKER_NODE] - %(message)s')
logger = logging.getLogger(__name__)

URL_SAAS = "http://127.0.0.1:8080"
URL_OLLAMA = "http://localhost:11434/api/generate"
MODELO_IA = "qwen2.5:7b"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CARGA DE IDENTIDAD ---
with open(os.path.join(BASE_DIR, "identidades.json"), "r", encoding="utf-8") as f:
    ident = json.load(f)
    if "random" in sys.argv:
        worker_acc = Keypair()
        logger.info(f"Usando identidad temporal: {worker_acc.pubkey()}")
    else:
        worker_acc = Keypair.from_bytes(bytes(ident["Worker"]["private"]))

ENABLE_SKILLS = True

# --- MOTOR DE SKILLS (PARCHEADO CONTRA RCE) ---

async def ejecutar_skill_local(skill_path, args):
    """Ejecuta un script local con sanitización de argumentos (PARCHE 1)."""
    script_path = os.path.join(skill_path, "run.py")
    if not os.path.exists(script_path):
        script_path = os.path.join(skill_path, "scripts", "run.py")
    
    if not os.path.exists(script_path):
        return "Error: Script de ejecución no encontrado."

    # Sanitización estricta (PARCHE 1): Solo permitimos caracteres seguros
    # Eliminamos cualquier intento de inyectar pipes, redirecciones o múltiples comandos
    args_str = str(args)
    sanitized_args = re.sub(r'[^a-zA-Z0-9\s\-_./]', '', args_str)
    
    cmd = [sys.executable, script_path, sanitized_args]
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode().strip()
        else:
            return f"Error en skill: {stderr.decode().strip()}"
    except Exception as e:
        return f"Excepción ejecutando skill: {e}"

# --- LÓGICA DE HERRAMIENTAS ---

def cargar_skills_tools():
    skills_map = {
        "web_search": os.path.join(BASE_DIR, "skills", "web_search"),
        "filesystem": os.path.join(BASE_DIR, "skills", "filesystem")
    }
    return skills_map

# --- PROCESAMIENTO CON IA ---

async def procesar_con_ia(prompt, skills_map):
    """Usa Ollama para razonar sobre la tarea y decidir si usar skills."""
    # En un entorno real, aquí se usaría la API de tools de Ollama. 
    # Para este parche, simulamos la respuesta de texto.
    payload = {
        "model": MODELO_IA,
        "prompt": f"Eres un agente autónomo. Tarea: {prompt}. Responde solo con el resultado final.",
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(URL_OLLAMA, json=payload) as resp:
            data = await resp.json()
            return data.get("response", "Error de procesamiento")

# --- CICLO DE TRABAJO ---

async def worker_task(session, sem, tarea):
    async with sem:
        worker_pk_str = str(worker_acc.pubkey())
        logger.info(f"🛠️ Trabajando en tarea #{tarea['id']}")

        # 1. Aceptar tarea
        async with session.post(f"{URL_SAAS}/aceptar_tarea/{tarea['id']}", 
                               json={"worker_pubkey": worker_pk_str}) as r:
            if r.status != 200:
                return

        # 2. Ejecutar lógica
        skills_map = cargar_skills_tools()
        resultado = await procesar_con_ia(tarea['tarea'], skills_map)

        # 3. PARCHE 3: FIRMA DE INTEGRIDAD (ID:HASH)
        # Creamos un hash del resultado para que el SaaS verifique que no fue alterado
        resultado_hash = hashlib.sha256(resultado.encode()).hexdigest()
        mensaje_a_firmar = f"{tarea['id']}:{resultado_hash}"
        
        # Firmar el mensaje
        firma_bytes = worker_acc.sign_message(mensaje_a_firmar.encode())
        firma_lista = list(bytes(firma_bytes))

        # 4. Enviar al SaaS
        payload_final = {
            "tarea_id": tarea['id'],
            "worker_pubkey": worker_pk_str,
            "resultado": resultado,
            "firma": firma_lista
        }

        async with session.post(f"{URL_SAAS}/finalizar_tarea", json=payload_final) as r:
            res_json = await r.json()
            logger.info(f"✅ Tarea #{tarea['id']} enviada. Status: {res_json.get('status')}")

async def ejecutar():
    sem = asyncio.Semaphore(2) # Máximo 2 tareas simultáneas
    logger.info(f"🚀 Worker iniciado: {worker_acc.pubkey()}")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(f"{URL_SAAS}/listar_tareas") as r:
                    if r.status == 200:
                        tareas = await r.json()
                        for t in tareas:
                            # Evitar repetir tareas ya hechas
                            await worker_task(session, sem, t)
                
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error en bucle: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(ejecutar())