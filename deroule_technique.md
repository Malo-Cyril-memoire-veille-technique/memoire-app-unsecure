# DÉROULÉ TECHNIQUE DU PROJET – Messagerie non sécurisée et démonstration MITM

---

### 1. Architecture technique

Le projet repose sur une infrastructure composée de **quatre conteneurs Docker** interconnectés sur un même réseau `secure_net` :

* **`poc-server`** : serveur d’application recevant et stockant les messages.
* **`client_a`** et **`client_b`** : deux clients en ligne de commande simulant des utilisateurs humains.
* **`mitm-proxy`** : un proxy TCP jouant le rôle d’un attaquant interposé (Man-in-the-Middle).

Le serveur est exposé sur le port `5000`. Les clients ne se connectent pas directement à lui, mais via le proxy MITM (`HOST=mitm-proxy`), ce qui permet l’interception du trafic.

---

### 2. Fonctionnement de l’application

L'application est une **messagerie non sécurisée** :

* **Aucune authentification forte** : l’utilisateur s’authentifie avec un mot de passe, mais les messages sont transmis uniquement avec un `token` UUID stocké côté serveur.
* **Aucun chiffrement** : les messages sont transmis en clair (JSON sur TCP), donc lisibles et modifiables par n’importe quel intermédiaire.
* **Aucune signature numérique** : un champ `"sender"` est automatiquement déterminé par le `token`, mais rien n’empêche un acteur tiers de l’usurper si les vérifications sont contournées.

Le client interroge régulièrement le serveur pour récupérer les nouveaux messages (polling), et les stocke localement dans des fichiers JSON pour afficher un historique conversationnel.

---

### 3. MITM simplifié dans le POC

Dans une attaque MITM réelle, l’attaquant intercepte le trafic réseau en :

* se plaçant entre les deux parties (via ARP spoofing, DNS poisoning, ou rogue AP),
* analysant ou modifiant le trafic TCP ou TLS.

Ici, cette **attaque est simulée par un proxy TCP** (fichier `mitm-proxy.py`) qui agit comme intermédiaire réseau.

Ce proxy :

* intercepte toutes les requêtes JSON entre les clients et le serveur,
* affiche les messages en clair (interception passive),
* peut bloquer ou modifier les messages selon des règles (`BLOCKED_KEYWORDS`, `MODIFICATIONS`),
* peut également injecter des messages arbitraires dans le système en usurpant une identité (`token="MITM_FAKE"` + `sender` manuellement défini).

Ce modèle est **plus simple que la réalité**, mais permet de **démontrer de façon claire** les effets d’une attaque MITM sur un protocole vulnérable.

#### Cas réel MITM

Dans une attaque Man-in-the-Middle réelle, l’attaquant ne contrôle pas directement la configuration du client. Il doit donc détourner le trafic réseau à son insu. Cela se fait généralement par :

* **ARP spoofing** : l’attaquant se fait passer pour la passerelle réseau sur un réseau local.
* **DNS spoofing** : il fournit de fausses résolutions de noms de domaine.
* **Rogue Access Point** : il intercepte le trafic via un faux point d’accès Wi-Fi.

Une fois le trafic redirigé, si les échanges ne sont pas chiffrés, l’attaquant peut lire, modifier, bloquer ou injecter des messages sans être détecté.

---

### 4. Points faibles volontairement conservés

Le système présente des faiblesses intentionnelles pour les besoins du POC :

| Élément          | Faiblesse                                          |
| ---------------- | -------------------------------------------------- |
| Authentification | Token UUID stocké en clair et facilement spoofable |
| Confidentialité  | Aucune couche de chiffrement                       |
| Intégrité        | Messages modifiables sans détection                |
| Authenticité     | Pas de signature numérique → usurpation triviale   |
| Transport        | Pas de TLS, communication directe en clair sur TCP |

Ces failles sont typiques d’un protocole applicatif non sécurisé, tel qu’on pourrait le retrouver dans des applications naïves ou des projets étudiants.

---

### 5. Justification des choix

* L’utilisation de Docker permet de compartimenter proprement chaque rôle (client, serveur, attaquant).
* Le format JSON est facilement lisible et modifiable, ce qui facilite la démonstration pédagogique.
* L'absence de TLS est volontaire pour permettre l’interception transparente du trafic.
* Le système de `token` non signé illustre l'importance de mécanismes cryptographiques d’intégrité et d’authentification.

---

### 6. Ce que ce POC démontre

Ce projet démontre clairement que :

* sans mécanismes de sécurité adaptés, une messagerie est vulnérable à toute forme de manipulation de contenu,
* un MITM peut agir à la fois en observateur, censeur et auteur de messages,
* les utilisateurs n’ont **aucun moyen de détecter la compromission** sans vérification d’intégrité ou de provenance.