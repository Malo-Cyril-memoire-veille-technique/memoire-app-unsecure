import socket
import threading
import os
import json
import uuid
import hashlib
import time
import logging

LOG_FOLDER = "logs"
os.makedirs(LOG_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(os.path.join(LOG_FOLDER, "server.log"))]
)

HOST = '0.0.0.0'
PORT = 5000
DATA_FOLDER = 'data'
USERS_FILE = os.path.join(DATA_FOLDER, 'users.json')
SESSIONS_FILE = os.path.join(DATA_FOLDER, 'sessions.json')
MESSAGES_FILE = os.path.join(DATA_FOLDER, 'messages.json')

os.makedirs(DATA_FOLDER, exist_ok=True)

for file in [USERS_FILE, SESSIONS_FILE, MESSAGES_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(path):
    """
    Charge les données d'un fichier JSON.
    :param path: Chemin du fichier.
    :return: Données chargées.
    """
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    """
    Enregistre les données dans un fichier JSON.
    :param path: Chemin du fichier.
    :param data: Données à enregistrer.
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def handle_client(conn):
    """
    Gère la connexion d'un client.
    :param conn: La connexion du client.
    """
    with conn:
        data = conn.recv(8192).decode()
        if not data:
            return
        try:
            req = json.loads(data)
        except json.JSONDecodeError:
            logging.warning("Requête invalide reçue (JSONDecodeError)")
            conn.sendall(json.dumps({"status": "error", "message": "invalid json"}).encode())
            return

        action = req.get("action")
        if action != "get_messages":
            logging.info(f"Requête reçue : action={action} → {json.dumps(req)}")

        if action == "register":
            username = req.get("username")
            password = req.get("password")
            if not username or not password:
                logging.warning("Tentative d'inscription avec champs manquants")
                conn.sendall(json.dumps({"status": "error", "message": "missing credentials"}).encode())
                return
            users = load_json(USERS_FILE)
            if username in users:
                logging.warning(f"Nom d'utilisateur déjà pris : {username}")
                conn.sendall(json.dumps({"status": "error", "message": "username already exists"}).encode())
                return
            users[username] = hashlib.sha256(password.encode()).hexdigest()
            save_json(USERS_FILE, users)
            logging.info(f"Compte créé : {username}")
            conn.sendall(json.dumps({"status": "ok", "message": "user created"}).encode())

        elif action == "login":
            username = req.get("username")
            password = req.get("password")
            users = load_json(USERS_FILE)
            hashed_input = hashlib.sha256(password.encode()).hexdigest()
            if users.get(username) != hashed_input:
                logging.warning(f"Connexion refusée pour {username} (mauvais mot de passe)")
                conn.sendall(json.dumps({"status": "error", "message": "invalid credentials"}).encode())
                return
            sessions = load_json(SESSIONS_FILE)
            token = str(uuid.uuid4())
            sessions[token] = username
            save_json(SESSIONS_FILE, sessions)
            logging.info(f"Connexion réussie : {username} → token={token}")
            conn.sendall(json.dumps({"status": "ok", "token": token}).encode())

        elif action == "logout":
            token = req.get("token")
            sessions = load_json(SESSIONS_FILE)
            user = sessions.pop(token, None)
            save_json(SESSIONS_FILE, sessions)
            logging.info(f"Déconnexion de {user} (token={token})")
            conn.sendall(json.dumps({"status": "ok"}).encode())

        elif action == "send_message":
            token = req.get("token")
            to = req.get("to")
            message = req.get("message")

            if token == "MITM_FAKE":
                sender = req.get("sender")
                logging.info(f"Message injecté par MITM : {sender} → {to} : {message}")
            else:
                sessions = load_json(SESSIONS_FILE)
                sender = sessions.get(token)

            if not sender or not to or not message:
                logging.warning("Envoi de message refusé (champs manquants ou non autorisé)")
                conn.sendall(json.dumps({"status": "error", "message": "missing or unauthorized"}).encode())
                return

            msgs = load_json(MESSAGES_FILE)
            msgs.setdefault(to, []).append({
                "sender": sender,
                "timestamp": int(time.time()),
                "message": message
            })
            save_json(MESSAGES_FILE, msgs)
            logging.info(f"Message stocké de {sender} vers {to} : {message}")
            conn.sendall(json.dumps({"status": "ok"}).encode())

        elif action == "get_messages":
            token = req.get("token")
            sessions = load_json(SESSIONS_FILE)
            user = sessions.get(token)
            if not user:
                conn.sendall(json.dumps({"status": "error", "message": "unauthorized"}).encode())
                return
            msgs = load_json(MESSAGES_FILE)
            conn.sendall(json.dumps({"status": "ok", "messages": msgs.get(user, [])}).encode())

        else:
            logging.warning(f"Action inconnue reçue : {action}")
            conn.sendall(json.dumps({"status": "error", "message": "unknown action"}).encode())

def start_server():
    """
    Démarre le serveur et écoute les connexions entrantes.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Démarré sur {HOST}:{PORT}")
        logging.info(f"Démarré sur {HOST}:{PORT}")
        while True:
            conn, _ = s.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

if __name__ == '__main__':
    start_server()
