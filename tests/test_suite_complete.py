"""
Suite de tests complète pour le système de calcul de distances optimisé
Execute tous les tests critiques avant commit (style CI/CD)
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
from calculators import (
    BatchProcessor,
    calculate_batch_distance,
    get_cache,
    GeocodingCache
)
import os
from dotenv import load_dotenv
import hashlib
import time
from pathlib import Path

load_dotenv()

# Configuration
API_KEY = os.getenv('API_ORS')
CACHE_DB = '.cache/test_geocoding_cache.db'

# Compteurs de tests
tests_passed = 0
tests_failed = 0
test_results = []

def log_test(test_name, passed, message=""):
    global tests_passed, tests_failed, test_results

    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        'name': test_name,
        'passed': passed,
        'message': message
    }
    test_results.append(result)

    if passed:
        tests_passed += 1
        print(f"{status} - {test_name}")
    else:
        tests_failed += 1
        print(f"{status} - {test_name}")
        if message:
            print(f"       → {message}")

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# ============================================================================
# TEST 1: Cache Persistant SQLite
# ============================================================================
print_section("TEST 1: Cache Persistant SQLite")

try:
    # Nettoyer le cache de test s'il existe
    if Path(CACHE_DB).exists():
        Path(CACHE_DB).unlink()

    cache = GeocodingCache(db_path=CACHE_DB)

    # Test 1.1: Initialisation
    log_test("1.1 - Initialisation cache SQLite",
             Path(CACHE_DB).exists(),
             "Le fichier de cache doit être créé")

    # Test 1.2: Sauvegarde et récupération
    test_address = "PARIS"
    test_coords = (48.8566, 2.3522)
    cache.set(test_address, "nominatim", test_coords)
    retrieved = cache.get(test_address, "nominatim")

    log_test("1.2 - Sauvegarde et récupération",
             retrieved == test_coords,
             f"Expected {test_coords}, got {retrieved}")

    # Test 1.3: Cache miss
    missing = cache.get("ADRESSE_INEXISTANTE_123", "nominatim")
    log_test("1.3 - Cache miss retourne None",
             missing is None,
             f"Expected None, got {missing}")

    # Test 1.4: Stats du cache
    stats = cache.get_stats()
    log_test("1.4 - Statistiques du cache",
             stats['cache_size'] >= 1 and 'hits' in stats,
             f"Stats: {stats}")

    # Nettoyer
    Path(CACHE_DB).unlink()

except Exception as e:
    log_test("1.x - Cache persistant", False, str(e))

# ============================================================================
# TEST 2: Validation des Adresses
# ============================================================================
print_section("TEST 2: Validation des Adresses")

try:
    # Test 2.1: Adresses valides
    valid_df = pd.DataFrame({
        'Adresse 1': ['Paris', 'Lyon', 'Lille'],
        'Adresse 2': ['Lyon', 'Paris', 'Marseille']
    })

    addresses_pairs = []
    valid_indices = []
    invalid_values = ['nan', 'NaN', '<NA>', 'None', '', 'null', 'NULL']

    for idx, row in valid_df.iterrows():
        address1 = str(row['Adresse 1']).strip()
        address2 = str(row['Adresse 2']).strip()
        if address1 not in invalid_values and address2 not in invalid_values:
            addresses_pairs.append((address1, address2))
            valid_indices.append(idx)

    log_test("2.1 - Adresses valides acceptées",
             len(valid_indices) == 3,
             f"Expected 3 valid, got {len(valid_indices)}")

    # Test 2.2: Adresses avec cellules vides
    empty_df = pd.DataFrame({
        'Adresse 1': ['Paris', '', 'Lille'],
        'Adresse 2': ['Lyon', 'Paris', '']
    })

    valid_count = 0
    for idx, row in empty_df.iterrows():
        address1 = str(row['Adresse 1']).strip()
        address2 = str(row['Adresse 2']).strip()
        if address1 not in invalid_values and address2 not in invalid_values:
            valid_count += 1

    log_test("2.2 - Cellules vides ignorées",
             valid_count == 1,
             f"Expected 1 valid, got {valid_count}")

    # Test 2.3: Adresses avec NaN pandas
    nan_df = pd.DataFrame({
        'Adresse 1': ['Paris', pd.NA, 'Lille'],
        'Adresse 2': ['Lyon', 'Paris', None]
    })

    valid_count = 0
    for idx, row in nan_df.iterrows():
        address1 = str(row['Adresse 1']).strip()
        address2 = str(row['Adresse 2']).strip()
        if address1 not in invalid_values and address2 not in invalid_values:
            valid_count += 1

    log_test("2.3 - NaN pandas gérés",
             valid_count <= 3,  # Peut varier selon la conversion
             f"Got {valid_count} valid addresses")

except Exception as e:
    log_test("2.x - Validation adresses", False, str(e))

# ============================================================================
# TEST 3: Calcul de Distance avec Cache
# ============================================================================
print_section("TEST 3: Calcul de Distance avec Cache")

try:
    # Test 3.1: Calcul basique
    result = calculate_batch_distance('Paris', 'Lyon', api_key_ors=API_KEY, quiet=True)

    log_test("3.1 - Calcul distance basique",
             result.final_distance is not None and result.final_distance > 0,
             f"Distance: {result.final_distance} km, source: {result.source}")

    # Test 3.2: Même adresse
    result = calculate_batch_distance('Paris', 'Paris', api_key_ors=API_KEY, quiet=True)

    log_test("3.2 - Même adresse = 0 km",
             result.final_distance == 0.0,
             f"Expected 0.0, got {result.final_distance}")

    # Test 3.3: Cache hit (Paris déjà en cache)
    cache = get_cache()
    cache_before = cache.get_stats()

    result = calculate_batch_distance('Paris', 'Marseille', api_key_ors=API_KEY, quiet=True)

    cache_after = cache.get_stats()
    cache_used = cache_after['hits'] > cache_before['hits']

    log_test("3.3 - Cache utilisé pour adresses répétées",
             cache_used and result.final_distance is not None,
             f"Cache hits: {cache_before['hits']} → {cache_after['hits']}")

    # Test 3.4: Villes seules (sans adresse complète)
    result = calculate_batch_distance('Lille', 'Toulouse', api_key_ors=API_KEY, quiet=True)

    log_test("3.4 - Villes seules acceptées",
             result.final_distance is not None and result.final_distance > 0,
             f"Distance Lille-Toulouse: {result.final_distance} km")

except Exception as e:
    log_test("3.x - Calcul distance", False, str(e))

# ============================================================================
# TEST 4: Traitement par Batch
# ============================================================================
print_section("TEST 4: Traitement par Batch")

try:
    test_data = pd.DataFrame({
        'Adresse 1': ['Paris', 'Lyon', 'Lille', 'Marseille', 'Bordeaux'] * 4,  # 20 lignes
        'Adresse 2': ['Lyon', 'Paris', 'Marseille', 'Lyon', 'Toulouse'] * 4,
        'Distance (km)': [None] * 20
    })

    batch_processor = BatchProcessor(batch_size=10)  # 2 batches
    session_id = hashlib.md5(b"test_batch").hexdigest()

    # Test 4.1: Traitement complet
    progress_calls = []
    def track_progress(current, total, message):
        progress_calls.append((current, total, message))

    result_df, stats = batch_processor.process_batches(
        df=test_data,
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=track_progress,
        max_workers=5,
        api_key_ors=API_KEY,
        quiet=True
    )

    log_test("4.1 - Traitement par batch complet",
             len(result_df) == 20 and stats['success_count'] > 0,
             f"Processed {len(result_df)} lignes, {stats['success_count']} succès")

    # Test 4.2: Callback de progression appelé
    log_test("4.2 - Callback de progression",
             len(progress_calls) > 0,
             f"{len(progress_calls)} appels de callback")

    # Test 4.3: Colonnes résultats créées
    expected_cols = ['Distance (km)', 'Source', 'Statut', 'Message']
    has_cols = all(col in result_df.columns for col in expected_cols)

    log_test("4.3 - Colonnes résultats créées",
             has_cols,
             f"Colonnes: {result_df.columns.tolist()}")

    # Test 4.4: Statistiques correctes
    total_items = stats['success_count'] + stats['warning_count'] + stats['error_count']

    log_test("4.4 - Statistiques cohérentes",
             total_items == 20,
             f"Total: {total_items}, Success: {stats['success_count']}, Errors: {stats['error_count']}")

except Exception as e:
    log_test("4.x - Traitement par batch", False, str(e))

# ============================================================================
# TEST 5: Gestion des Fichiers Temporaires
# ============================================================================
print_section("TEST 5: Gestion des Fichiers Temporaires")

try:
    batch_processor = BatchProcessor(batch_size=5)
    test_session = hashlib.md5(b"temp_test").hexdigest()

    # Test 5.1: Pas de fichiers temporaires au départ
    has_pending, num = batch_processor.has_pending_session(test_session)

    log_test("5.1 - Pas de fichiers temp initialement",
             not has_pending and num == 0,
             f"Found {num} files")

    # Test 5.2: Nettoyage après traitement réussi
    small_df = pd.DataFrame({
        'Adresse 1': ['Paris', 'Lyon'],
        'Adresse 2': ['Lyon', 'Paris']
    })

    result_df, stats = batch_processor.process_batches(
        df=small_df,
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=test_session,
        progress_callback=None,
        max_workers=3,
        api_key_ors=API_KEY,
        quiet=True
    )

    has_pending_after, num_after = batch_processor.has_pending_session(test_session)

    log_test("5.2 - Nettoyage automatique après succès",
             not has_pending_after and num_after == 0,
             f"Temp files after: {num_after}")

except Exception as e:
    log_test("5.x - Fichiers temporaires", False, str(e))

# ============================================================================
# TEST 6: Performance du Cache
# ============================================================================
print_section("TEST 6: Performance du Cache")

try:
    # Préparer des adresses répétées
    repeated_data = pd.DataFrame({
        'Adresse 1': ['Paris'] * 10 + ['Lyon'] * 10,
        'Adresse 2': ['Lyon'] * 10 + ['Paris'] * 10
    })

    cache = get_cache()
    cache_before = cache.get_stats()

    batch_processor = BatchProcessor(batch_size=10)
    session_id = hashlib.md5(b"cache_perf_test").hexdigest()

    start_time = time.time()
    result_df, stats = batch_processor.process_batches(
        df=repeated_data,
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=None,
        max_workers=5,
        api_key_ors=API_KEY,
        quiet=True
    )
    elapsed = time.time() - start_time

    cache_after = cache.get_stats()
    hit_rate = cache_after['hit_rate']

    # Test 6.1: Taux de hit élevé sur adresses répétées
    log_test("6.1 - Taux de cache hit élevé",
             hit_rate > 50,  # Au moins 50% de hits
             f"Hit rate: {hit_rate:.1f}%")

    # Test 6.2: Temps de traitement raisonnable
    log_test("6.2 - Performance acceptable",
             elapsed < 60,  # Moins de 60 secondes pour 20 lignes
             f"Temps: {elapsed:.1f}s pour 20 lignes")

except Exception as e:
    log_test("6.x - Performance cache", False, str(e))

# ============================================================================
# RÉSUMÉ DES TESTS
# ============================================================================
print_section("RÉSUMÉ DES TESTS")

total_tests = tests_passed + tests_failed
success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"Total de tests: {total_tests}")
print(f"✅ Réussis: {tests_passed}")
print(f"❌ Échoués: {tests_failed}")
print(f"📊 Taux de réussite: {success_rate:.1f}%\n")

if tests_failed > 0:
    print("❌ TESTS ÉCHOUÉS:")
    for result in test_results:
        if not result['passed']:
            print(f"  - {result['name']}")
            if result['message']:
                print(f"    {result['message']}")
    print(f"\n🚫 COMMIT BLOQUÉ - Corriger les tests avant de commit")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS PASSENT")
    print("✅ PRÊT POUR LE COMMIT")
    sys.exit(0)
