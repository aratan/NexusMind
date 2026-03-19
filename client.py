# -*- coding: utf-8 -*-
import requests, time, json, logging, sys
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.compute_budget import set_compute_unit_price
from solders.transaction import Transaction
from solders.message import Message
from datetime import datetime

# Configuración de salida para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [CLIENT] - %(message)s')
logger = logging.getLogger(__name__)

URL_SAAS = "http://127.0.0.1:8080"
sol_client = SolanaClient("https://api.devnet.solana.com")

def ejecutar():
    try:
        with open("identidades.json", "r", encoding="utf-8") as f:
            ident = json.load(f)
            cli_kp = Keypair.from_bytes(bytes(ident["Cliente"]["private"]))
    except Exception as e:
        logger.error(f"Error cargando identidades: {e}")
        return

    # Tarea a realizar
    tarea_texto = f"Realiza un análisis de sentimiento profundo sobre las últimas noticias de Solana. Fecha: {datetime.now().strftime('%Y-%m-%d')}"
    pago_sol = 0.01

    # PASO 1: Solicitar Tarea incluyendo nuestra PubKey (PARCHE 2)
    logger.info("Solicitando tarea al SaaS...")
    payload_solicitud = {
        "cliente": "Victor_Batou",
        "cliente_pubkey": str(cli_kp.pubkey()), # Identidad vinculada desde el inicio
        "tarea": tarea_texto,
        "pago": pago_sol
    }
    
    try:
        r = requests.post(f"{URL_SAAS}/solicitar_tarea", json=payload_solicitud)
        res = r.json()
        tarea_id = res["id"]
        escrow_pubkey = res["escrow_pubkey"]
        logger.info(f"Tarea #{tarea_id} creada. Escrow: {escrow_pubkey}")
    except Exception as e:
        logger.error(f"Error al crear tarea: {e}")
        return

    # PASO 2: Pago al Escrow en Solana
    logger.info(f"Enviando {pago_sol} SOL al Escrow...")
    try:
        recent_blockhash = sol_client.get_latest_blockhash().value.blockhash
        ix = transfer(TransferParams(
            from_pubkey=cli_kp.pubkey(),
            to_pubkey=Pubkey.from_string(escrow_pubkey),
            lamports=int(pago_sol * 10**9)
        ))
        # Añadimos priority fees para evitar bloqueos
        prioridad = set_compute_unit_price(50_000)
        msg = Message([prioridad, ix], cli_kp.pubkey())
        tx = Transaction([cli_kp], msg, recent_blockhash)
        
        tx_hash = sol_client.send_transaction(tx).value
        logger.info(f"Pago enviado. TX: {tx_hash}")
        
        # Espera de confirmación en blockchain
        logger.info("Esperando confirmación de red (30s)...")
        time.sleep(30)
    except Exception as e:
        logger.error(f"Error en la transacción: {e}")
        return

    # PASO 3: Confirmar Pago al SaaS
    try:
        payload_confirmar = {
            "tarea_id": tarea_id,
            "pago_tx": str(tx_hash)
        }
        r = requests.post(f"{URL_SAAS}/confirmar_pago_tarea", json=payload_confirmar)
        if r.status_code == 200:
            logger.info("✅ SaaS ha verificado el pago. Tarea en cola.")
        else:
            logger.error(f"❌ Error verificando pago: {r.text}")
            return
    except Exception as e:
        logger.error(f"Error de red: {e}")
        return

    # PASO 4: Monitoreo de Resultados
    logger.info("Esperando resultados (Consenso)...")
    while True:
        try:
            r = requests.get(f"{URL_SAAS}/consultar_tarea/{tarea_id}")
            data = r.json()
            estado = data.get("estado")

            if estado == "finalizada":
                print("\n" + "═"*60)
                print(f"✅ RESULTADO OBTENIDO:\n\n{data.get('resultado')}")
                print(f"🏆 Ganadores: {data.get('workers_ganadores')}")
                print(f"🔗 TX Pago: {data.get('tx_hash_worker')}")
                print("═"*60 + "\n")
                break
            elif estado == "fallida_sin_consenso":
                logger.error("La tarea falló por falta de consenso entre workers.")
                break
            
            # Feedback visual de progreso
            activos = len(data.get('workers_activos', []))
            recibidos = len(data.get('resultados_recibidos', []))
            sys.stdout.write(f"\r[STATUS] {estado.upper()} | Workers activos: {activos} | Resultados: {recibidos}/3 ")
            sys.stdout.flush()
            
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error consultando: {e}")
            break

if __name__ == "__main__":
    ejecutar()