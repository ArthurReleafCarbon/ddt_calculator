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
streamlit run app.py
```

## 🔑 Clé API OpenRouteService

Pour activer la validation croisée des distances :
1. Obtenez une clé gratuite sur [openrouteservice.org](https://openrouteservice.org)
2. Ajoutez-la dans votre fichier `.env` : `API_ORS=votre_cle`

## 📊 Validation des distances

Le système calcule automatiquement avec 2 services et sélectionne la valeur la plus fiable :
- **Différence < 10%** → Moyenne des deux valeurs
- **Différence > 10%** → Valeur la plus petite
- **Distance > 300 km** → Rejetée automatiquement (aberrante)

Tous les détails de validation sont affichés dans le terminal.

## 🛠️ Technologies utilisées

- **Streamlit** : Interface web
- **Pandas** : Traitement des données
- **Geopy** : Calcul de distances géodésiques
- **OpenRouteService** : Géolocalisation
- **Nominatim** : Géolocalisation gratuite

## 📝 Licence

Usage interne - Calcul des émissions domicile-travail
