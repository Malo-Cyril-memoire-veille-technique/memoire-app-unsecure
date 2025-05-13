# DÉMONSTRATION : Vulnérabilité d'une messagerie non sécurisée à une attaque de type Man-in-the-Middle (MITM)

---

### Objectif

Montrer qu’une messagerie sans chiffrement ni signature est vulnérable à plusieurs types d’attaques :

* L’interception passive des messages
* La modification ou la censure active
* L’injection de faux messages avec usurpation d’identité

---

### Environnement

L'infrastructure repose sur quatre conteneurs Docker :

* `poc-server` : serveur de messagerie
* `client_a` : utilisateur A
* `client_b` : utilisateur B
* `mitm-proxy` : proxy attaquant interposé (MITM)

Les clients communiquent avec le serveur via le proxy `mitm-proxy`, qui intercepte tout le trafic.

---

## Étapes de la démonstration

---

### 1. Lancement de l’environnement

Commandes à exécuter dans un terminal :

```bash
docker-compose up
```

Cette commande démarre tous les conteneurs.

---

### 2. Création des comptes

Depuis un terminal :

```bash
docker-compose run client_a
```

Dans l’interface :

* Créer un compte nommé `a`
* Se connecter
* Envoyer un message à l'utilisateur `b`

Même procédure avec :

```bash
docker-compose run client_b
```

* Créer un compte `b`
* Lire les messages reçus

À ce stade, les messages circulent normalement via le proxy MITM.

---

### 3. Interception passive des messages

Dans un autre terminal, afficher les logs du proxy :

```bash
docker-compose logs -f mitm-proxy
```

Tous les messages envoyés entre les clients sont affichés en clair dans les logs.
Cela démontre qu’aucun chiffrement n’est mis en place.

---

### 4. Blocage d’un message par mot interdit

Depuis `client_a`, envoyer le message suivant :

```
voici mon motdepasse
```

Le message est bloqué par le proxy car il contient un mot présent dans la liste `BLOCKED_KEYWORDS`.

Dans les logs du proxy, on observe :

```
📥 Requête client (ORIGINAL): ...
📥 Requête client ❌ Message bloqué (mot interdit : 'motdepasse')
```

Le message n’est pas reçu par `b`.

---

### 5. Modification d’un message à la volée

Envoyer depuis `client_a` :

```
ce document est topsecret
```

Le proxy modifie automatiquement ce message selon les règles définies dans `MODIFICATIONS`.

Par exemple :

```python
MODIFICATIONS = {
    "topsecret": "censuré"
}
```

Dans les logs :

```
📥 Requête client (ORIGINAL): "ce document est topsecret"
📥 Requête client (MODIFIÉ): "ce document est censuré"
```

L'utilisateur `b` reçoit un message modifié sans en avoir conscience.

---

### 6. Injection d’un faux message (usurpation)

Dans un terminal séparé, lancer le conteneur interactif du proxy :

```bash
docker-compose run mitm-proxy
```

Dans l’interface interactive du proxy :

```
> De (expéditeur) : a
> À (destinataire) : b
> Message : t'es viré
```

Le message est envoyé par le proxy en usurpant l’identité de `a`.
Du point de vue de `b`, le message apparaît comme étant authentique.

Dans la discussion chez `b` :

```
[14:xx] a : t'es viré
```

Cela prouve qu’il est possible d’injecter des messages arbitraires sans être authentifié.

---

## Conclusion

Cette démonstration met en évidence les vulnérabilités suivantes dans la messagerie :

* Les messages sont lisibles en clair sur le réseau
* Aucune vérification d’intégrité : les messages peuvent être modifiés
* Aucune authentification : un attaquant peut se faire passer pour un autre utilisateur

Une messagerie sans chiffrement ni signature est donc totalement exposée à un attaquant positionné entre les utilisateurs.