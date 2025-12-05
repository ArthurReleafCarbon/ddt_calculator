# 🧪 Suite de Tests - Calculateur de Distances

## 📋 Vue d'ensemble

Cette suite de tests valide l'ensemble du système de calcul de distances optimisé, incluant :
- Cache persistant SQLite
- Validation des adresses
- Calcul de distances avec APIs
- Traitement par batch
- Gestion des fichiers temporaires
- Performance du cache

## 🚀 Exécution des Tests

### Test Complet (Style CI/CD)

```bash
python tests/test_suite_complete.py
```

Ce test exécute **19 tests** couvrant toutes les fonctionnalités critiques.
- ✅ Exit code 0 = Tous les tests passent
- ❌ Exit code 1 = Au moins un test échoué

### Tests de Debug

#### Analyser un fichier Excel spécifique
```bash
python tests/debug_mon_fichier.py /chemin/vers/fichier.xlsx
```
Utile pour débugger le problème "Adresse manquante".

#### Tester différents cas d'adresses invalides
```bash
python tests/debug_adresse_manquante.py
```

## 📊 Couverture des Tests

### 1️⃣ Cache Persistant SQLite (4 tests)
- ✅ 1.1 - Initialisation cache SQLite
- ✅ 1.2 - Sauvegarde et récupération
- ✅ 1.3 - Cache miss retourne None
- ✅ 1.4 - Statistiques du cache

### 2️⃣ Validation des Adresses (3 tests)
- ✅ 2.1 - Adresses valides acceptées
- ✅ 2.2 - Cellules vides ignorées
- ✅ 2.3 - NaN pandas gérés

### 3️⃣ Calcul de Distance avec Cache (4 tests)
- ✅ 3.1 - Calcul distance basique
- ✅ 3.2 - Même adresse = 0 km
- ✅ 3.3 - Cache utilisé pour adresses répétées
- ✅ 3.4 - Villes seules acceptées

### 4️⃣ Traitement par Batch (4 tests)
- ✅ 4.1 - Traitement par batch complet
- ✅ 4.2 - Callback de progression
- ✅ 4.3 - Colonnes résultats créées
- ✅ 4.4 - Statistiques cohérentes

### 5️⃣ Gestion des Fichiers Temporaires (2 tests)
- ✅ 5.1 - Pas de fichiers temp initialement
- ✅ 5.2 - Nettoyage automatique après succès

### 6️⃣ Performance du Cache (2 tests)
- ✅ 6.1 - Taux de cache hit élevé (>50%)
- ✅ 6.2 - Performance acceptable (<60s pour 20 lignes)

## 🎯 Taux de Réussite Actuel

**100% ✅** - 19/19 tests passent

## 📁 Fichiers de Test

| Fichier | Description |
|---------|-------------|
| `test_suite_complete.py` | Suite complète CI/CD (19 tests) |
| `debug_mon_fichier.py` | Analyse un fichier Excel spécifique |
| `debug_adresse_manquante.py` | Test des cas d'adresses invalides |
| `test_batch_resume.py` | Test de reprise après crash |
| `test_batch_crash_simulation.py` | Simulation de crash pendant traitement |
| `test_manual_resume.py` | Test manuel étape par étape |

## 🔧 Prérequis

- Python 3.8+
- Dépendances: `pandas`, `openpyxl`, `geopy`, `requests`
- Fichier `.env` avec `API_ORS` (optionnel, Nominatim fonctionne sans)

## 💡 Utilisation en CI/CD

Intégrer dans votre pipeline :

```yaml
# .github/workflows/tests.yml
- name: Run Tests
  run: python tests/test_suite_complete.py
```

Le script retourne un code de sortie approprié :
- `0` = Succès (prêt pour commit/deploy)
- `1` = Échec (corriger avant commit)
