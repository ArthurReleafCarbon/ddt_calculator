# 📐 Architecture du projet

## Vue d'ensemble

Application Streamlit pour calculer automatiquement les distances domicile-travail avec validation croisée et optimisations de performance.

## Structure des dossiers

```
auto_dist_ddt/
│
├── 📄 home.py                      # Point d'entrée principal de l'application
├── 📄 config.py                    # Gestion des secrets (API keys)
├── 📄 Makefile                     # Commandes utiles (install, streamlit)
├── 📄 requirements.txt             # Dépendances Python
│
├── 📁 .streamlit/                  # Configuration Streamlit
│   ├── config.toml                 # Thème et paramètres
│   └── secrets.toml                # Secrets (ignoré par git)
│
├── 📁 pages/                       # Pages Streamlit (navigation multi-pages)
│   ├── Calculette Distance.py     # Calcul par lots (batch)
│   └── Calculette Domicile-Travail.py  # Calcul avec bilan carbone
│
├── 📁 calculators/                 # 🧮 Logique de calcul de distances
│   ├── __init__.py                 # Exports du package
│   ├── distance_calculator.py     # Calcul de base avec Nominatim/ORS
│   ├── dual_distance_calculator.py # Validation croisée 2 services
│   ├── batch_distance_calculator.py # Calcul par lots (version standard)
│   ├── batch_distance_calculator_optimized.py # ⚡ Version optimisée
│   ├── geocoding_cache.py         # Cache des géolocalisations
│   └── summary_calculator.py      # Récapitulatifs et statistiques
│
├── 📁 validation/                  # ✅ Validation de fichiers
│   ├── __init__.py
│   └── excel_validator.py         # Validation format Excel
│
├── 📁 tests/                       # 🧪 Tests et benchmarks
│   ├── __init__.py
│   └── test_performance.py        # Test de performance
│
└── 📁 Documentation
    ├── README.md                   # Documentation principale
    ├── DEPLOYMENT.md               # Guide de déploiement
    ├── OPTIMIZATIONS.md            # Documentation des optimisations
    └── ARCHITECTURE.md             # Ce fichier
```

## Flux de données

### 1. Calculette Distance (Batch)

```
User Upload Excel
       ↓
Calculette Distance.py
       ↓
batch_distance_calculator_optimized.py
       ↓
   ┌───┴───┐
   ↓       ↓
Nominatim  ORS (cache utilisé)
   ↓       ↓
   └───┬───┘
       ↓
Validation croisée
       ↓
Excel avec distances
```

### 2. Calculette Domicile-Travail

```
User Upload Excel
       ↓
excel_validator.py (validation format)
       ↓
Calculette Domicile-Travail.py
       ↓
dual_distance_calculator.py
       ↓
   ┌───┴───┐
   ↓       ↓
Nominatim  ORS
   ↓       ↓
   └───┬───┘
       ↓
summary_calculator.py (récapitulatif)
       ↓
Excel avec 2 feuilles (données + récap)
```

## Modules principaux

### 📦 calculators/

#### `distance_calculator.py`
- **Rôle** : Calcul de base des distances
- **Services** : Nominatim (OSM) et OpenRouteService
- **Fonctions principales** :
  - `calculate_distance()` : Calcul simple
  - `get_coordinates_nominatim()` : Géolocalisation gratuite
  - `get_coordinates_ors()` : Géolocalisation avec clé API
  - `normalize_commune_name()` : Normalisation des noms de villes

#### `dual_distance_calculator.py`
- **Rôle** : Validation croisée entre 2 services
- **Logique** :
  - Différence < 10% → Moyenne
  - Différence > 10% → Plus petite valeur
  - Distance > 300 km → Rejetée (aberrante)

#### `batch_distance_calculator_optimized.py` ⚡
- **Rôle** : Calcul optimisé pour gros volumes
- **Optimisations** :
  - Parallélisation (ThreadPoolExecutor, 5 workers)
  - Cache des géolocalisations
  - Mode quiet (réduit logs)
- **Gains** : x3 à x5 selon CPU et doublons

#### `geocoding_cache.py`
- **Rôle** : Cache en mémoire des coordonnées GPS
- **Bénéfices** :
  - Évite appels API répétés
  - Économie de 50-90% sur doublons
  - Statistiques (hit rate)

#### `summary_calculator.py`
- **Rôle** : Génération de récapitulatifs
- **Sorties** :
  - Récap par mode de transport
  - Récap par type de véhicule
  - Statistiques globales

### 📦 validation/

#### `excel_validator.py`
- **Rôle** : Validation des fichiers Excel uploadés
- **Vérifications** :
  - Format des colonnes
  - Présence des champs obligatoires
  - Types de données
  - Cohérence des valeurs

### 📦 pages/

#### `Calculette Distance.py`
- **Mode** : Calcul par lots (batch)
- **Input** : Excel avec 2 colonnes d'adresses
- **Output** : Excel avec distances + validation
- **Spécificités** :
  - Aucun plafond de distance
  - Affichage statistiques cache
  - Temps d'exécution affiché

#### `Calculette Domicile-Travail.py`
- **Mode** : Bilan carbone domicile-travail
- **Input** : Excel format Releaf Carbon
- **Output** : Excel avec 2 feuilles
  1. Données enrichies avec distances
  2. Récapitulatif par mode de transport
- **Spécificités** :
  - Calcul distances annuelles
  - Prise en compte jours fériés
  - Validation stricte du format

## Configuration

### `config.py`
Gestion centralisée des secrets avec fallback :
1. Priorité 1 : `st.secrets` (Streamlit Cloud)
2. Priorité 2 : `.env` (développement local)

### `.streamlit/secrets.toml`
Format pour Streamlit Cloud :
```toml
[secrets]
API_ORS = "votre_cle_api"
```

## Dépendances

- **streamlit** : Framework web
- **pandas** : Manipulation de données
- **openpyxl** : Lecture/écriture Excel
- **geopy** : Calcul distances géodésiques
- **requests** : Appels HTTP aux APIs
- **python-dotenv** : Gestion .env (local)

## Patterns de conception

### 1. Séparation des responsabilités
- **UI** : Pages Streamlit
- **Logique métier** : Calculators
- **Validation** : Validators
- **Configuration** : config.py

### 2. Cache Pattern
- Implémentation singleton du cache
- Invalidation au début de chaque calcul
- Statistiques pour monitoring

### 3. Strategy Pattern
- Plusieurs stratégies de calcul :
  - Standard (séquentiel)
  - Optimisé (parallèle + cache)
  - Dual validation (2 services)

### 4. Builder Pattern
- `BatchDistanceResult` : Objet résultat structuré
- Contient toutes les métadonnées du calcul

## Performances

### Métriques typiques
- **10 adresses** : ~12s (optimisé) vs ~40s (standard)
- **50 adresses** : ~50s (optimisé) vs ~200s (standard)
- **100 adresses** : ~80s (optimisé) vs ~400s (standard)

### Facteurs d'optimisation
1. **Parallélisation** : x3-5
2. **Cache (30% doublons)** : x1.5-2
3. **Mode quiet** : x1.1-1.15

## Évolutions futures

### Court terme
- [ ] Barre de progression plus précise en mode parallèle
- [ ] Export CSV en plus d'Excel
- [ ] Historique des calculs

### Moyen terme
- [ ] Cache persistant (SQLite/Redis)
- [ ] API REST pour intégrations externes
- [ ] Batch API pour ORS si disponible

### Long terme
- [ ] Machine learning pour détecter adresses aberrantes
- [ ] Support multi-utilisateurs
- [ ] Dashboard analytics temps réel

## Contribuer

1. Respecter la structure des dossiers
2. Ajouter des tests dans `tests/`
3. Documenter les nouvelles fonctionnalités
4. Mettre à jour ce fichier si architecture change

## Maintenance

### Tester après modifications
```bash
# Test imports
python -c "from calculators import *; from validation import *"

# Test performance
python tests/test_performance.py

# Lancer l'app
make streamlit
```

### Ajout d'un nouveau calculateur
1. Créer le fichier dans `calculators/`
2. Ajouter les imports dans `calculators/__init__.py`
3. Documenter dans ce fichier
4. Créer un test dans `tests/`
