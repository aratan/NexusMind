# -*- coding: utf-8 -*-
import json, logging, os, sys, difflib, hashlib
from flask import Flask, request, jsonify, render_template
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.compute_budget import set_compute_unit_price
from solders.transaction import Transaction
from solders.message import Message
from solders.signature import Signature
import threading
import time

# Configuración UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- CONFIGURACIÓN DE LOGS ---
log_formatter = logging.Formatter('%(asctime)s - [SAAS_WEB] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler('saas_audit.log', encoding='utf-8')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

app = Flask(__name__, static_folder='static', template_folder='templates')
solana_client = SolanaClient("https://api.devnet.solana.com")
DB_FILE = "tareas_db.json"
tareas_memoria = []
reputacion_db = {}

# --- PARCHEO CRÍTICO: SEGURIDAD ---
CONSENSUS_REQUIRED = 3  # Quórum mínimo para evitar ataques de un solo worker

# --- CARGA DE IDENTIDAD ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "identidades.json"), "r", encoding="utf-8") as f:
    ident = json.load(f)
    saas_acc = Keypair.from_bytes(bytes(ident["SaaS"]["private"]))

# --- FUNCIONES DE APOYO Y SEGURIDAD ---

def verificar_pago_cliente(tx_hash, monto_esperado, escrow_pubkey_str, cliente_esperado):
    """PARCHE 2: Valida identidad del pagador para evitar secuestro de tareas."""
    try:
        sig = Signature.from_string(tx_hash)
        tx_data = solana_client.get_transaction(sig, max_supported_transaction_version=0)
        if tx_data.value is None: return False, None
        meta = tx_data.value.transaction.meta
        if meta is None or meta.err is not None: return False, None
        
        msg = tx_data.value.transaction.transaction.message
        account_keys = msg.account_keys
        
        # Validar que quien pagó en Solana sea el mismo que pidió la tarea
        remitente_real = str(account_keys[0])
        if remitente_real != cliente_esperado:
            logger.warning(f"⚠️ Intento de fraude: Pagador {remitente_real} no coincide con {cliente_esperado}")
            return False, None

        escrow_index = account_keys.index(Pubkey.from_string(escrow_pubkey_str))
        balance_diff = meta.post_balances[escrow_index] - meta.pre_balances[escrow_index]
        if balance_diff >= int(float(monto_esperado) * 10**9):
            return True, remitente_real
        return False, None
    except Exception as e:
        logger.error(f"Error en validación Solana: {e}")
        return False, None

def guardar_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(tareas_memoria, f, indent=4, ensure_ascii=False)

def cargar_db():
    global tareas_memoria, reputacion_db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            tareas_memoria = json.load(f)
        for t in tareas_memoria:
            if t.get('estado') == 'finalizada':
                for g in t.get('workers_ganadores', []):
                    if g not in reputacion_db: reputacion_db[g] = {"exitos": 0, "fallos": 0}
                    reputacion_db[g]["exitos"] += 1

def penalizar_worker(worker_pk):
    if worker_pk not in reputacion_db: reputacion_db[worker_pk] = {"exitos": 0, "fallos": 0}
    reputacion_db[worker_pk]["fallos"] += 1

def premiar_worker(worker_pk):
    if worker_pk not in reputacion_db: reputacion_db[worker_pk] = {"exitos": 0, "fallos": 0}
    reputacion_db[worker_pk]["exitos"] += 1

# --- RUTAS DE VISUALIZACIÓN (FRONTEND) ---

@app.route('/')
def index():
    return render_template('index.html', wallet=str(saas_acc.pubkey()))

@app.route('/api/stats', methods=['GET'])
def api_stats():
    try:
        completadas = [t for t in tareas_memoria if t.get('estado') == 'finalizada'][-10:]
        volumen_total = sum(float(t.get('pago_total', 0)) for t in tareas_memoria)
        
        workers_ranking = []
        for pk, data in reputacion_db.items():
            workers_ranking.append({"pk": pk[:8] + "...", "exitos": data["exitos"], "fallos": data["fallos"]})
        
        return jsonify({
            "total": len(tareas_memoria),
            "exitos": len([t for t in tareas_memoria if t.get('estado') == 'finalizada']),
            "volumen": volumen_total,
            "workers_stats": sorted(workers_ranking, key=lambda x: x["exitos"], reverse=True)[:5]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tareas', methods=['GET'])
def api_tareas():
    tareas_reverse = tareas_memoria[::-1]
    return jsonify({"tareas": tareas_reverse[:20]})

# --- ENDPOINTS CORE (API PARA WORKER Y CLIENTE) ---

@app.route('/solicitar_tarea', methods=['POST'])
def solicitar_tarea():
    data = request.json
    escrow_kp = Keypair()
    tarea_id = len(tareas_memoria) + 1
    nueva_tarea = {
        "id": tarea_id,
        "cliente": data.get('cliente', 'Victor_Batou'),
        "cliente_pubkey_esperada": data.get('cliente_pubkey'), # PARCHE 2
        "tarea": data.get('tarea'),
        "pago_total": float(data.get('pago', 0.02)),
        "estado": "esperando_pago",
        "escrow_priv": list(bytes(escrow_kp)),
        "escrow_pub": str(escrow_kp.pubkey()),
        "resultados_recibidos": [],
        "workers_activos": [],
        "workers_ganadores": [],
        "tx_hash_worker": None
    }
    tareas_memoria.append(nueva_tarea)
    guardar_db()
    return jsonify({"status": "ok", "id": tarea_id, "escrow_pubkey": str(escrow_kp.pubkey())})

@app.route('/confirmar_pago_tarea', methods=['POST'])
def confirmar_pago_tarea():
    data = request.json
    tarea = next((t for t in tareas_memoria if t['id'] == data.get('tarea_id')), None)
    if not tarea or tarea['estado'] != 'esperando_pago': return jsonify({"error": "No válida"}), 400

    es_valido, remitente = verificar_pago_cliente(
        data.get('pago_tx'), tarea['pago_total'], tarea['escrow_pub'], tarea.get('cliente_pubkey_esperada')
    )
    
    if not es_valido: return jsonify({"error": "Pago no verificado o remitente incorrecto"}), 402

    tarea['estado'] = 'pendiente'
    tarea['pago_tx_cliente'] = data.get('pago_tx')
    tarea['cliente_pubkey'] = remitente
    guardar_db()
    return jsonify({"status": "pago_confirmado"})

def realizar_pagos_solana(tarea):
    """Ejecuta la liquidación de fondos desde el Escrow a los Workers ganadores."""
    try:
        escrow_kp = Keypair.from_bytes(bytes(tarea["escrow_priv"]))
        balance = solana_client.get_balance(escrow_kp.pubkey()).value
        if balance == 0: return

        pago_worker = int((balance * 0.8) / len(tarea["workers_ganadores"]))
        instrucciones = [set_compute_unit_price(100_000)]
        
        for winner in tarea["workers_ganadores"]:
            instrucciones.append(transfer(TransferParams(
                from_pubkey=escrow_kp.pubkey(), to_pubkey=Pubkey.from_string(winner), lamports=pago_worker
            )))
        
        # El SaaS cobra el 20% restante como comisión
        instrucciones.append(transfer(TransferParams(
            from_pubkey=escrow_kp.pubkey(), to_pubkey=saas_acc.pubkey(), lamports=balance - (pago_worker * len(tarea["workers_ganadores"]))
        )))

        blockhash = solana_client.get_latest_blockhash().value.blockhash
        txn = Transaction([saas_acc, escrow_kp], Message(instrucciones, saas_acc.pubkey()), blockhash)
        tx_res = solana_client.send_transaction(txn)
        tarea["tx_hash_worker"] = [str(tx_res.value)]
    except Exception as e:
        logger.error(f"Error en liquidación Solana: {e}")

def evaluar_consenso(tarea):
    # Si ya tenemos suficientes resultados, forzamos una decisión
    if len(tarea["resultados_recibidos"]) < CONSENSUS_REQUIRED: return
    
    votos = {}
    for r in tarea["resultados_recibidos"]:
        texto = r["resultado"]
        encontrado = False
        for k in votos.keys():
            # Subimos un poco la tolerancia al 60% para que los LLM coincidan más fácil
            if difflib.SequenceMatcher(None, k, texto).ratio() > 0.60:
                votos[k].append(r["worker_pubkey"])
                encontrado = True
                break
        if not encontrado: votos[texto] = [r["worker_pubkey"]]
    
    # Elegimos el grupo con más votos
    ganador_texto = max(votos, key=lambda k: len(votos[k]))
    votos_ganadores = len(votos[ganador_texto])

    # Si tenemos mayoría o ya hemos recibido el doble del quórum (ej. 6 resultados)
    if votos_ganadores >= (CONSENSUS_REQUIRED // 2 + 1) or len(tarea["resultados_recibidos"]) >= 6:
        logger.info(f"🏆 Consenso alcanzado para Tarea #{tarea['id']} con {votos_ganadores} votos.")
        tarea["estado"] = "finalizada"
        tarea["resultado"] = ganador_texto
        tarea["workers_ganadores"] = votos[ganador_texto]
        for g in tarea["workers_ganadores"]: premiar_worker(g)
        realizar_pagos_solana(tarea)
        guardar_db()

    
@app.route('/finalizar_tarea', methods=['POST'])
def finalizar_tarea():
    req = request.json
    tarea = next((t for t in tareas_memoria if t['id'] == req.get('tarea_id')), None)
    
    if not tarea: return jsonify({"error": "No existe"}), 404
    if tarea['estado'] == 'finalizada': return jsonify({"status": "ya_completada"})
    
    # PARCHE 3: Validación ID:HASH
    resultado_recibido = str(req.get('resultado', ''))
    res_hash = hashlib.sha256(resultado_recibido.encode()).hexdigest()
    mensaje_esperado = f"{tarea['id']}:{res_hash}"
    
    worker_pk = Pubkey.from_string(req['worker_pubkey'])
    firma = Signature.from_bytes(bytes(req['firma']))
    
    if not firma.verify(worker_pk, mensaje_esperado.encode()):
        return jsonify({"error": "Firma inválida o alteración detectada"}), 403

    if not any(w["pk"] == req['worker_pubkey'] for w in tarea.get("workers_activos", [])):
        return jsonify({"error": "No asignado"}), 403
        
    tarea["resultados_recibidos"].append({
        "worker_pubkey": req['worker_pubkey'],
        "resultado": resultado_recibido[:50000]
    })
    tarea["workers_activos"] = [w for w in tarea["workers_activos"] if w["pk"] != req['worker_pubkey']]
    
    evaluar_consenso(tarea)
    guardar_db()
    return jsonify({"status": "recibido"})

@app.route('/listar_tareas', methods=['GET'])
def listar_tareas():
    return jsonify([t for t in tareas_memoria if t['estado'] == 'pendiente'])

@app.route('/aceptar_tarea/<int:tarea_id>', methods=['POST'])
def aceptar_tarea(tarea_id):
    worker_pubkey = request.json.get("worker_pubkey")
    tarea = next((t for t in tareas_memoria if t['id'] == tarea_id), None)
    if tarea and tarea['estado'] == 'pendiente':
        tarea["workers_activos"].append({"pk": worker_pubkey, "timestamp": time.time()})
        if len(tarea["workers_activos"]) >= CONSENSUS_REQUIRED:
            tarea['estado'] = 'procesando'
        guardar_db()
        return jsonify({"status": "asignado"})
    return jsonify({"error": "Ocupada"}), 400

@app.route('/consultar_tarea/<int:tarea_id>', methods=['GET'])
def consultar_tarea(tarea_id):
    tarea = next((t for t in tareas_memoria if t['id'] == tarea_id), None)
    return jsonify(tarea) if tarea else ({"error": "404"}, 404)

# --- WORKER TTL CHECKER (MANTENIMIENTO) ---
def ttl_checker():
    while True:
        ahora = time.time()
        for t in tareas_memoria:
            if t["estado"] in ["pendiente", "procesando"]:
                # Eliminar workers que no responden
                caducados = [w["pk"] for w in t.get("workers_activos", []) if ahora - w.get("timestamp", ahora) > 600]
                if caducados:
                    t["workers_activos"] = [w for w in t["workers_activos"] if w["pk"] not in caducados]
                    for wpk in caducados: penalizar_worker(wpk)
                
                # REPARACIÓN: Si no hay nadie trabajando en ella, volver a 'pendiente'
                # para que otros workers la vean y completen el consenso (1/3 -> 3/3)
                if len(t["workers_activos"]) == 0 and t["estado"] == "procesando":
                    logger.info(f"♻️ Tarea #{t['id']} re-activada por falta de workers.")
                    t["estado"] = "pendiente"
                
                guardar_db()
        time.sleep(30)

if __name__ == "__main__":
    cargar_db()
    threading.Thread(target=ttl_checker, daemon=True).start()
    logger.info("⚡ SAAS WEB COMPLETO Y SEGURO INICIADO ⚡")
    app.run(port=8080, debug=False)