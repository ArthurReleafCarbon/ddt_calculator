# 🚗 Calculateur de Distance Domicile-Travail

Application Streamlit pour calculer automatiquement les distances domicile-travail et générer des bilans carbone.

## 🌟 Fonctionnalités

- ✅ **Validation automatique** du fichier Excel en entrée
- ✅ **Calcul parallèle** avec Nominatim et OpenRouteService
- ✅ **Validation croisée** pour garantir la précision des distances
- ✅ **Filtrage intelligent** des valeurs aberrantes (> 300 km)
- ✅ **Calcul automatique** des distances annuelles
- ✅ **Récapitulatif détaillé** par mode de transport et type de véhicule
- ✅ **Export Excel** avec 2 feuilles (données + récapitulatif)

## 📋 Format du fichier Excel

Le fichier doit contenir une feuille nommée "Questionnaire dom-travail" avec :
- **Ligne 6** : En-têtes de colonnes
- **Ligne 7+** : Données

### Colonnes obligatoires :
- **F** : Commune de résidence
- **G** : Nombre de jours travaillés sur site par semaine
- **H** : Moyen de transport principal
- **I** : Catégorie de voiture (obligatoire si transport = voiture)
- **J** : Énergie de voiture (obligatoire si transport = voiture)
- **L** : Lieu de travail

## 🚀 Déploiement local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Créer un fichier .env avec votre clé API (optionnel mais recommandé)
echo "API_ORS=votre_cle_ici" > .env

# Lancer l'application
streamlit run home.py
# ou utiliser le Makefile
make streamlit
```

## 🔑 Clé API OpenRouteService

Pour activer la validation croisée des distances :
1. Obtenez une clé gratuite sur [openrouteservice.org](https://openrouteservice.org)
2. **En local** : Ajoutez-la dans votre fichier `.env` : `API_ORS=votre_cle`
3. **Sur Streamlit Cloud** : Ajoutez-la dans les **Secrets** de l'app (Settings > Secrets) :
   ```toml
   [secrets]
   API_ORS = "votre_cle_ici"
   ```

## ☁️ Déploiement sur Streamlit Cloud

1. Poussez votre code sur GitHub
2. Allez sur [share.streamlit.io](https://share.streamlit.io)
3. Connectez votre repository
4. Spécifiez `home.py` comme fichier principal
5. Ajoutez votre clé API dans **Settings > Secrets** :
   ```toml
   [secrets]
   API_ORS = "votre_cle_ici"
   ```
6. Déployez !

## 📊 Validation des distances

Le système calcule automatiquement avec 2 services et sélectionne la valeur la plus fiable :
- **Différence < 10%** → Moyenne des deux valeurs
- **Différence > 10%** → Valeur la plus petite
- **Distance > 300 km** → Rejetée automatiquement (aberrante)

Tous les détails de validation sont affichés dans le terminal.

## 📁 Structure du projet

```
/
├── home.py                          # Point d'entrée de l'application
├── config.py                        # Gestion des secrets (API keys)
├── calculators/                     # Modules de calcul de distances
│   ├── distance_calculator.py
│   ├── dual_distance_calculator.py
│   ├── batch_distance_calculator.py
│   ├── batch_distance_calculator_optimized.py  # Version optimisée
│   ├── geocoding_cache.py          # Cache des géolocalisations
│   └── summary_calculator.py
├── validation/                      # Validation de fichiers Excel
│   └── excel_validator.py
├── tests/                          # Scripts de test
│   └── test_performance.py
└── pages/                          # Pages Streamlit
    ├── Calculette Distance.py
    └── Calculette Domicile-Travail.py
```

## 🛠️ Technologies utilisées

- **Streamlit** : Interface web
- **Pandas** : Traitement des données
- **Geopy** : Calcul de distances géodésiques
- **OpenRouteService** : Géolocalisation
- **Nominatim** : Géolocalisation gratuite

## 📝 Licence

Usage interne - Calcul des émissions domicile-travail
