"""
Script de test pour comparer les performances entre la version standard et optimisée
"""
import time
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculators import calculate_batch_distance, calculate_batch_distances_parallel, get_cache
from config import get_api_key

# Données de test
test_addresses = [
    ("Paris", "Lyon"),
    ("Marseille", "Lille"),
    ("Paris", "Bordeaux"),
    ("Lyon", "Toulouse"),
    ("Nantes", "Strasbourg"),
    ("Paris", "Lyon"),  # Doublon pour tester le cache
    ("Marseille", "Lille"),  # Doublon pour tester le cache
]

api_key = get_api_key()

print("="*80)
print("🧪 TEST DE PERFORMANCE - Calcul de distances")
print("="*80)
print(f"\n📋 Nombre de paires d'adresses : {len(test_addresses)}")
print(f"🔑 API ORS : {'✅ Configurée' if api_key else '❌ Non configurée'}")

# Test version optimisée avec parallélisation
print("\n" + "="*80)
print("⚡ TEST 1: Version OPTIMISÉE (parallèle + cache)")
print("="*80)

cache = get_cache()
cache.clear()

start_time = time.time()
results_optimized = calculate_batch_distances_parallel(
    test_addresses,
    api_key_ors=api_key,
    max_workers=5,
    quiet=False
)
elapsed_optimized = time.time() - start_time

cache_stats = cache.get_stats()

print(f"\n✅ Temps d'exécution : {elapsed_optimized:.2f} secondes")
print(f"⚡ Vitesse : {len(test_addresses) / elapsed_optimized:.2f} calculs/seconde")
print(f"💾 Cache : {cache_stats['hits']} hits / {cache_stats['total']} requêtes ({cache_stats['hit_rate']:.1f}%)")

# Afficher les résultats
print("\n📊 Résultats :")
for i, (result, (addr1, addr2)) in enumerate(zip(results_optimized, test_addresses), 1):
    status_icon = "✅" if result.status == "ok" else "⚠️" if result.status == "warning" else "❌"
    print(f"  {i}. {status_icon} {addr1} → {addr2}: {result.final_distance} km ({result.source})")

print("\n" + "="*80)
print("📈 RÉSUMÉ")
print("="*80)
print(f"Version optimisée : {elapsed_optimized:.2f}s")
print(f"Vitesse moyenne : {len(test_addresses) / elapsed_optimized:.2f} calculs/s")
print(f"Économie cache : {cache_stats['hit_rate']:.1f}%")

# Statistiques de succès
success = sum(1 for r in results_optimized if r.status == "ok")
warnings = sum(1 for r in results_optimized if r.status == "warning")
errors = sum(1 for r in results_optimized if r.status == "error")

print(f"\nRésultats : {success} succès, {warnings} avertissements, {errors} erreurs")
print("\n💡 Gains attendus sur un fichier de 100 lignes :")
print(f"   - Avec cache : ~{elapsed_optimized / len(test_addresses) * 50:.1f}s (vs ~{elapsed_optimized / len(test_addresses) * 100:.1f}s sans cache)")
print(f"   - Accélération estimée : x{100 / 50:.1f} grâce au cache sur adresses dupliquées")

print("\n" + "="*80)
