# WebSemantics - Application de Recherche Alimentaire

Bienvenue sur WebSemantics, une application web moderne pour explorer, rechercher et visualiser des aliments et leurs images à partir d'une base de connaissances sémantique.

## Fonctionnalités principales
- **Recherche Global** : trouvez des aliments par nom, catégorie, région, etc.
- **Affichage de tous les aliments** : parcourez la base complète.
- **Visualisation d'images** : affichez l'image principale ou toutes les images d'un aliment.
- **Suggestions de recherche** : obtenez des suggestions pour corriger ou compléter vos requêtes.
- **Interface moderne** : navigation par onglets, design responsive et agréable.

---

## Prérequis
- **Python 3.8+**
- **pip** (gestionnaire de paquets Python)
- **Docker** (optionnel, recommandé pour Elasticsearch et Fuseki)
- Un navigateur web moderne (Chrome, Firefox, Edge...)

---

## Installation et démarrage

### 1. Cloner le projet
```bash
git clone https://github.com/Achaire-Zogo/WebSemantics.git
cd WebSemantics
```

### 2. Installer les dépendances Python
```bash
pip install -r requirements.txt
```

### 3. Lancer les services nécessaires

#### a) Avec Docker (recommandé)
Lancez Fuseki et Elasticsearch avec :
```bash
docker-compose up -d
```

#### b) Sans Docker
- **Fuseki** : Téléchargez et lancez Apache Jena Fuseki sur le port 3030.
- **Elasticsearch** : Lancez Elasticsearch sur le port 9200.

### 4. Démarrer le backend Flask
```bash
cd service
python app.py
```
Le backend sera accessible sur [http://localhost:8080](http://localhost:8080)

### 5. Utiliser le frontend
Ouvrez le fichier `frontend/index.html` dans votre navigateur (double-cliquez ou faites clic droit > ouvrir avec...)

---

## Utilisation de l'application

- **Onglet Recherche** : Tapez un aliment et cliquez sur "Rechercher". Les résultats s'affichent comme sur Google, avec images et infos.
- **Onglet Tous les repas** : Cliquez sur "Afficher tous les aliments" pour voir toute la base.
- **Onglet Image principale** : Entrez le nom d'un aliment pour voir sa photo principale.
- **Onglet Image par index** : Entrez le nom d'un aliment et un numéro pour voir une image précise.
- **Onglet Suggestions** : Entrez un mot pour obtenir des suggestions de recherche.

---

## Astuces pour débutants
- Si rien ne s'affiche, vérifiez que le backend est bien lancé et que les services (Fuseki, Elasticsearch) sont actifs.
- Les images s'affichent si elles existent dans la base. Si une image ne s'affiche pas, essayez un autre aliment ou un autre index.
- Pour toute erreur, relisez le message affiché à l'écran ou dans le terminal.

---

## Structure du projet
```
project/
├── frontend/         # Interface web (HTML, CSS, JS)
├── service/          # Backend Flask (app.py, etc.)
├── images/           # Images des aliments (optionnel)
├── requirements.txt  # Dépendances Python
├── docker-compose.yml# Lancement des services
└── README.md         # Ce guide
```

---

## Support
Pour toute question ou problème, contactez l'auteur ou ouvrez une issue sur le dépôt Git.

Bonne découverte de WebSemantics !

## Contributor

- ACHAIRE ZOGO