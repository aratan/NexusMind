import json
import os
import time
from solana.rpc.api import Client as SolanaClient
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message

FILE_NAME = "identidades.json"

def guardar_cuentas(cuentas):
    data = {name: {"public": str(kp.pubkey()), "private": list(kp.to_bytes())} 
            for name, kp in cuentas.items()}
    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Identidades guardadas en {FILE_NAME}")

def cargar_cuentas():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            data = json.load(f)
        print("📂 Cargando identidades existentes...")
        return {name: Keypair.from_bytes(bytes(info["private"])) for name, info in data.items()}
    else:
        print("🆕 Creando nuevo ecosistema de cuentas...")
        cuentas = {
            "Client": Keypair(),
            "SaaS": Keypair(),
            "Worker": Keypair()
        }
        guardar_cuentas(cuentas)
        return cuentas

# 1. Inicialización
rpc_url = "https://api.devnet.solana.com"
client_rpc = SolanaClient(rpc_url)
cuentas = cargar_cuentas()

# Referencias rápidas
client_acc = cuentas["Client"]
saas_acc = cuentas["SaaS"]

print(f"\n--- Ecosistema Ara v26 ---")
print(f"Bóveda (Client): {client_acc.pubkey()}")
print(f"Servicio (SaaS): {saas_acc.pubkey()}")
print(f"Operativo (Worker): {cuentas['Worker'].pubkey()}\n")

# 2. Comprobar saldo antes de operar (Capa de Disponibilidad Real)
balance = client_rpc.get_balance(client_acc.pubkey()).value
print(f"Saldo actual en Bóveda: {balance / 10**9} SOL")

if balance < 100_000_000: # Si hay menos de 0.1 SOL, pedimos fondos
    print("Saldo insuficiente para transferencia. Intentando airdrop...")
    try:
        client_rpc.request_airdrop(client_acc.pubkey(), 1_000_000_000)
        print("Petición de fondos enviada. Espera 20s y vuelve a ejecutar el script.")
    except Exception as e:
        print(f"⚠️ Error en Faucet: {e}. Usa https://faucet.solana.com/")
else:
    # 3. Lógica de transferencia si hay saldo
    try:
        print("Iniciando transferencia Bóveda -> SaaS...")
        recent_blockhash = client_rpc.get_latest_blockhash().value.blockhash
        ix = transfer(TransferParams(
            from_pubkey=client_acc.pubkey(),
            to_pubkey=saas_acc.pubkey(),
            lamports=50_000_000 # 0.05 SOL
        ))
        msg = Message([ix], client_acc.pubkey())
        txn = Transaction([client_acc], msg, recent_blockhash)
        res = client_rpc.send_transaction(txn)
        print(f"✅ Flujo completado. Hash: {res.value}")
    except Exception as e:
        print(f"❌ Error operativo: {e}")

# 4. Comprobar saldo después de operar