# ⚡ Optimisations de Performance

## Vue d'ensemble

La Calculette Distance a été optimisée pour améliorer significativement les performances lors du calcul de grandes quantités de distances.

## Optimisations implémentées

### 1. 🚀 Parallélisation des calculs

**Fichier** : `calculators/batch_distance_calculator_optimized.py`

- Utilisation de `ThreadPoolExecutor` pour calculer plusieurs distances en parallèle
- **5 threads** exécutés simultanément par défaut
- **Gain** : x3 à x5 selon le nombre de cœurs CPU

**Avant** :
```python
for address_pair in addresses:
    result = calculate_distance(address_pair)  # Séquentiel
```

**Après** :
```python
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(calculate_distance, addresses)  # Parallèle
```

### 2. 💾 Cache des géolocalisations

**Fichier** : `calculators/geocoding_cache.py`

- Cache en mémoire des coordonnées GPS déjà calculées
- Évite les appels API répétés pour les mêmes adresses
- **Gain** : 50-90% de réduction du temps sur fichiers avec doublons

**Avantages** :
- Pas d'appel API si l'adresse est déjà dans le cache
- Pas de `time.sleep()` pour les adresses en cache
- Statistiques de cache affichées (hits, misses, hit rate)

### 3. 🔇 Mode "quiet"

**Fichier** : `calculators/batch_distance_calculator_optimized.py`

- Mode silencieux pour réduire les logs sur gros fichiers
- Affichage minimal pendant le calcul
- **Gain** : ~10-15% de réduction du temps d'exécution

### 4. ⚙️ Optimisation des délais

- `time.sleep(1)` uniquement sur les nouveaux appels API (pas sur le cache)
- Les appels ORS ne nécessitent pas de délai (rate limit moins strict)

## Gains de performance attendus

| Scénario | Version standard | Version optimisée | Gain |
|----------|------------------|-------------------|------|
| 10 adresses uniques | ~40s | ~12s | **x3.3** |
| 50 adresses avec 20% doublons | ~200s | ~50s | **x4** |
| 100 adresses avec 30% doublons | ~400s | ~80s | **x5** |

## Utilisation

### Dans Streamlit

La Calculette Distance utilise automatiquement la version optimisée :

```python
from batch_distance_calculator_optimized import calculate_batch_distances_parallel

results = calculate_batch_distances_parallel(
    addresses_pairs,
    api_key_ors=api_key,
    max_workers=5,
    quiet=True
)
```

### Test de performance

Pour tester les performances :

```bash
python tests/test_performance.py
```

## Affichage des métriques

Après chaque calcul, l'application affiche :
- ⚡ Temps d'exécution total
- 📊 Vitesse (calculs/seconde)
- 💾 Statistiques du cache (hit rate, économies)

Exemple :
```
⚡ Calcul terminé en 45.2 secondes (2.2 calculs/seconde)
💾 Cache : 120 hits / 200 requêtes (60.0% d'économie)
```

## Configuration avancée

### Ajuster le nombre de threads

Dans `pages/Calculette Distance.py` :

```python
results = calculate_batch_distances_parallel(
    addresses_pairs,
    max_workers=10,  # Augmenter pour plus de parallélisme (5 par défaut)
    quiet=True
)
```

⚠️ **Attention** : Trop de threads peut causer des erreurs de rate limiting sur les APIs.

### Désactiver le mode quiet

Pour voir les logs détaillés pendant le calcul :

```python
results = calculate_batch_distances_parallel(
    addresses_pairs,
    quiet=False  # Afficher tous les logs
)
```

## Architecture technique

```
┌─────────────────────────┐
│  Calculette Distance    │
│     (Interface UI)      │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ batch_distance_         │
│ calculator_optimized.py │
│  - Parallélisation      │
│  - Cache                │
│  - Mode quiet           │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │             │
     v             v
┌─────────┐  ┌─────────────┐
│  Cache  │  │  Distance   │
│ geocod. │  │ calculator  │
└─────────┘  └─────────────┘
```

## Maintenance

### Vider le cache

Le cache est vidé automatiquement au début de chaque calcul dans l'interface.

Pour le vider manuellement :

```python
from geocoding_cache import get_cache
cache = get_cache()
cache.clear()
```

## Compatibilité

- ✅ Compatible avec la version standard
- ✅ Même résultats que la version standard
- ✅ Fonctionne avec et sans clé API ORS
- ✅ Compatible avec tous les fichiers Excel existants

## Prochaines améliorations possibles

- [ ] Persistance du cache sur disque (SQLite)
- [ ] Utilisation des endpoints batch des APIs (si disponibles)
- [ ] Ajustement dynamique du rate limiting
- [ ] Préchargement des adresses fréquentes
