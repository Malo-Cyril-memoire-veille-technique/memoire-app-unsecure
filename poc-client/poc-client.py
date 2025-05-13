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
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(json.dumps(data).encode())
            return s.recv(8192).decode()
    except Exception as e:
        logging.error(f"❌ Erreur envoi requête : {e}")
        return json.dumps({"status": "error", "message": str(e)})

def create_account():
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
    global username, session_token
    username = input("Nom d'utilisateur : ").strip()
    password = getpass.getpass("Mot de passe : ").strip()
    response = send_request({"action": "login", "username": username, "password": password})
    result = json.loads(response)
    if result.get("status") == "ok":
        session_token = result.get("token")
        return True
    else:
        print("[ERREUR] Connexion échouée :", result.get("message"))
        return False

def logout():
    global session_token
    send_request({"action": "logout", "token": session_token})
    session_token = None

def save_sent_message(recipient, timestamp, text):
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
    path = os.path.join(HISTORY_FOLDER, f"{username}_to_{recipient}.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def load_received_messages(sender):
    path = os.path.join(HISTORY_FOLDER, f"{sender}_to_{username}.json")
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def get_messages():
    response = send_request({"action": "get_messages", "token": session_token})
    result = json.loads(response)
    if result.get("status") != "ok":
        return []
    return result.get("messages", [])

def get_conversation_partners():
    messages = get_messages()
    partners = set()
    for msg in messages:
        partners.add(msg.get("sender"))
    return sorted(partners)

def fetch_live_messages(target):
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
