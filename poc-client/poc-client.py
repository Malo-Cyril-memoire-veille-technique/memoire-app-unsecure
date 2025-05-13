import socket
import os
import json
import getpass
import threading
import time
import sys
from datetime import datetime
import logging

LOG_FOLDER = "logs"
HISTORY_FOLDER = "history"
os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)

container_name = socket.gethostname().lower()
log_file = f"{container_name}.log"
log_path = os.path.join(LOG_FOLDER, log_file)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(log_path, encoding='utf-8')]
)

HOST = os.environ.get("HOST", "poc-server")
PORT = 5000

session_token = None
username = ""
running = True

def send_request(data):
    """
    Envoie une requête au serveur et retourne la réponse.
    :param data: Données à envoyer.
    :return: Réponse du serveur.
    """
    try:
        if data.get("action") != "get_messages":
            logging.info(f"📤 Envoi requête : {json.dumps(data)}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps(data).encode())
            response = s.recv(8192).decode()
            if data.get("action") != "get_messages":
                logging.info(f"📥 Réponse : {response}")
            return response
    except Exception as e:
        logging.error(f"❌ Erreur envoi requête : {e}")
        return json.dumps({"status": "error", "message": str(e)})


def create_account():
    """
    Crée un compte utilisateur.
    """
    global username
    username = input("Créer un nom d'utilisateur : ").strip()
    password = getpass.getpass("Créer un mot de passe : ").strip()
    response = send_request({"action": "register", "username": username, "password": password})
    result = json.loads(response)
    if result.get("status") == "ok":
        print("[INFO] Compte créé avec succès.")
    else:
        print("[ERREUR] Impossible de créer le compte :", result.get("message"))

def login():
    """
    Connecte l'utilisateur.
    :return: True si la connexion est réussie, sinon False.
    """
    global username, session_token
    username = input("Nom d'utilisateur : ").strip()
    password = getpass.getpass("Mot de passe : ").strip()
    logging.info(f"🔑 Tentative de connexion : {username}")
    response = send_request({"action": "login", "username": username, "password": password})
    result = json.loads(response)
    if result.get("status") == "ok":
        session_token = result.get("token")
        logging.info(f"✅ Connexion réussie : {username}")
        return True
    else:
        logging.warning(f"❌ Connexion échouée : {username} → {result.get('message')}")
        print("[ERREUR] Connexion échouée :", result.get("message"))
        return False


def logout():
    """
    Déconnecte l'utilisateur.
    """
    global session_token
    logging.info(f"🚪 Déconnexion de {username}")
    send_request({"action": "logout", "token": session_token})
    session_token = None

def save_sent_message(recipient, timestamp, text):
    """
    Enregistre un message envoyé dans l'historique.
    :param recipient: Destinataire du message.
    :param timestamp: Horodatage du message.
    :param text: Contenu du message.
    """
    logging.info(f"✉️ Message envoyé à {recipient} à {timestamp} : {text}")
    path = os.path.join(HISTORY_FOLDER, f"{username}_to_{recipient}.json")
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except:
        data = []
    data.append({"timestamp": timestamp, "sender": username, "text": text})
    with open(path, 'w') as f:
        json.dump(data, f)

def save_received_message(sender, timestamp, text):
    """
    Enregistre un message reçu dans l'historique.
    :param sender: Expéditeur du message.
    :param timestamp: Horodatage du message.
    :param text: Contenu du message.
    """
    logging.info(f"📨 Message reçu de {sender} à {timestamp} : {text}")
    path = os.path.join(HISTORY_FOLDER, f"{sender}_to_{username}.json")
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except:
        data = []
    data.append({"timestamp": timestamp, "sender": sender, "text": text})
    with open(path, 'w') as f:
        json.dump(data, f)

def load_sent_messages(recipient):
    """
    Charge l'historique des messages envoyés à un destinataire.
    :param recipient: Destinataire des messages.
    :return: Liste des messages envoyés.
    """
    path = os.path.join(HISTORY_FOLDER, f"{username}_to_{recipient}.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def load_received_messages(sender):
    """
    Charge l'historique des messages reçus d'un expéditeur.
    :param sender: Expéditeur des messages.
    :return: Liste des messages reçus.
    """
    path = os.path.join(HISTORY_FOLDER, f"{sender}_to_{username}.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def get_messages():
    """
    Récupère les messages du serveur.
    :return: Liste des messages.
    """
    response = send_request({"action": "get_messages", "token": session_token})
    result = json.loads(response)
    if result.get("status") != "ok":
        return []
    return result.get("messages", [])

def get_conversation_partners():
    """
    Récupère la liste des partenaires de conversation.
    :return: Liste des partenaires de conversation.
    """
    messages = get_messages()
    partners = set()
    for msg in messages:
        partners.add(msg.get("sender"))
    return sorted(partners)

def fetch_live_messages(target):
    """
    Récupère les messages en temps réel pour une conversation donnée.
    :param target: Destinataire de la conversation.
    """
    global running
    seen = set()
    while running:
        messages = get_messages()
        for msg in messages:
            sender = msg.get("sender")
            timestamp = msg.get("timestamp")
            text = msg.get("message")
            key = f"{sender}:{timestamp}:{text}"
            if key in seen or sender != target:
                continue
            seen.add(key)
            t = datetime.fromtimestamp(timestamp).strftime("%H:%M")
            sys.stdout.write('\r' + ' ' * 80 + '\r')
            print(f"[{t}] {sender} : {text}")
            sys.stdout.write(f"{username} > ")
            sys.stdout.flush()
            save_received_message(sender, timestamp, text)
        time.sleep(1)

def chat_session(target):
    """
    Gère une session de chat avec un partenaire.
    :param target: Nom du partenaire de conversation.
    """
    global running
    print(f"\n[Conversation avec {target}] (tape 'exit' pour quitter)")

    messages = load_sent_messages(target) + load_received_messages(target)
    messages.sort(key=lambda m: m["timestamp"])
    for msg in messages:
        t = datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M")
        sender = msg["sender"]
        print(f"[{t}] {sender} : {msg['text']}")

    running = True
    listener = threading.Thread(target=fetch_live_messages, args=(target,), daemon=True)
    listener.start()

    try:
        while True:
            msg = input(f"{username} > ").strip()
            if msg.lower() == 'exit':
                break
            now = int(time.time())
            send_request({
                "action": "send_message",
                "token": session_token,
                "to": target,
                "message": msg
            })
            save_sent_message(target, now, msg)
    finally:
        running = False
        listener.join()

def discussion_menu():
    """
    Affiche le menu des discussions.
    """
    while True:
        print("\n--- DISCUSSIONS ---")
        partners = get_conversation_partners()
        for i, p in enumerate(partners):
            print(f"{i + 1}. {p}")
        print("c. Nouvelle conversation")
        print("q. Retour")
        choice = input("> ").strip().lower()
        if choice == 'q':
            break
        elif choice == 'c':
            target = input("Nom de l'utilisateur : ").strip()
            chat_session(target)
        elif choice.isdigit() and 1 <= int(choice) <= len(partners):
            chat_session(partners[int(choice) - 1])
        else:
            print("[ERREUR] Choix invalide.")

def main_menu():
    """
    Affiche le menu principal.
    """
    while True:
        print("\n--- MENU PRINCIPAL ---")
        print("1. Créer un compte")
        print("2. Se connecter")
        print("3. Quitter")
        choice = input("> ").strip()
        if choice == '1':
            create_account()
        elif choice == '2':
            if login():
                user_menu()
        elif choice == '3':
            break

def user_menu():
    """
    Affiche le menu utilisateur après connexion.
    """
    while True:
        print(f"\n[CLIENT: {username}] Menu")
        print("1. Discussions")
        print("2. Me déconnecter")
        choice = input("> ").strip()
        if choice == '1':
            discussion_menu()
        elif choice == '2':
            logout()
            print("[INFO] Déconnecté.")
            break

if __name__ == '__main__':
    main_menu()
