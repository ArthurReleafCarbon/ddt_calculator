"""
Script de test pour les optimisations :
- Cache persistant SQLite
- Traitement par batch avec sauvegarde temporaire
"""

import pandas as pd
from calculators import get_cache, BatchProcessor, calculate_batch_distance
from config import get_api_key
import time

def test_cache_persistant():
    """Test du cache persistant SQLite"""
    print("\n" + "="*80)
    print("TEST 1: Cache Persistant SQLite")
    print("="*80)

    cache = get_cache()

    # Afficher les infos du cache
    cache_info = cache.get_cache_info()
    print(f"\n📊 Informations du cache:")
    print(f"   - Nombre d'entrées: {cache_info.get('total_entries', 0)}")
    print(f"   - Taille DB: {cache_info.get('db_size_mb', 0)} MB")
    print(f"   - Chemin: {cache_info.get('db_path', 'N/A')}")

    # Test 1: Ajouter une adresse
    print("\n🔹 Test ajout adresse dans le cache...")
    cache.set("Paris", "nominatim", (48.8566, 2.3522))
    cache.set("Lyon", "nominatim", (45.7640, 4.8357))

    # Test 2: Récupérer une adresse
    print("🔹 Test récupération depuis le cache...")
    coords_paris = cache.get("Paris", "nominatim")
    print(f"   - Paris: {coords_paris}")

    coords_lyon = cache.get("Lyon", "nominatim")
    print(f"   - Lyon: {coords_lyon}")

    # Test 3: Statistiques
    stats = cache.get_stats()
    print(f"\n📈 Statistiques:")
    print(f"   - Hits: {stats['hits']}")
    print(f"   - Misses: {stats['misses']}")
    print(f"   - Taux de hit: {stats['hit_rate']:.1f}%")
    print(f"   - Taille cache: {stats['cache_size']} entrées")

    print("\n✅ Test cache persistant terminé")


def test_batch_processing():
    """Test du traitement par batch"""
    print("\n" + "="*80)
    print("TEST 2: Traitement par Batch avec Sauvegarde Temporaire")
    print("="*80)

    # Créer un DataFrame de test
    test_data = pd.DataFrame({
        'Adresse 1': [
            'Paris',
            'Lille',
            'Lyon',
            'Marseille',
            'Bordeaux',
            'Toulouse',
            'Nantes',
            'Strasbourg',
            'Montpellier',
            'Nice'
        ],
        'Adresse 2': [
            'Lyon',
            'Roubaix',
            'Paris',
            'Nice',
            'Toulouse',
            'Bordeaux',
            'Paris',
            'Paris',
            'Marseille',
            'Marseille'
        ],
        'Distance (km)': [None] * 10
    })

    print(f"\n📊 DataFrame de test: {len(test_data)} lignes")
    print(test_data.head())

    # Créer le BatchProcessor
    batch_processor = BatchProcessor(batch_size=3)

    # Charger la clé API
    api_key_ors = get_api_key()

    # Callback de progression
    def progress_callback(current, total, message):
        print(f"   📦 {message}: {current}/{total}")

    # Traiter par batch
    print("\n🚀 Démarrage du traitement par batch...")
    start_time = time.time()

    session_id = "test_session"

    try:
        result_df, stats = batch_processor.process_batches(
            df=test_data,
            process_function=calculate_batch_distance,
            address1_col='Adresse 1',
            address2_col='Adresse 2',
            session_id=session_id,
            progress_callback=progress_callback,
            max_workers=3,
            api_key_ors=api_key_ors,
            quiet=True
        )

        elapsed_time = time.time() - start_time

        print(f"\n✅ Traitement terminé en {elapsed_time:.1f} secondes")

        # Afficher les résultats
        print("\n📋 Résultats:")
        print(result_df[['Adresse 1', 'Adresse 2', 'Distance (km)', 'Statut']].to_string())

        # Afficher les statistiques
        print(f"\n📊 Statistiques:")
        print(f"   - Succès: {stats['success_count']}")
        print(f"   - Avertissements: {stats['warning_count']}")
        print(f"   - Erreurs: {stats['error_count']}")
        print(f"   - Total: {stats['total']}")

        # Stats du cache
        cache = get_cache()
        cache_stats = cache.get_stats()
        print(f"\n💾 Cache:")
        print(f"   - Hits: {cache_stats['hits']}")
        print(f"   - Misses: {cache_stats['misses']}")
        print(f"   - Taux de hit: {cache_stats['hit_rate']:.1f}%")
        print(f"   - Taille: {cache_stats['cache_size']} entrées")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    print("\n✅ Test traitement par batch terminé")


def test_crash_recovery():
    """Test de la récupération après crash"""
    print("\n" + "="*80)
    print("TEST 3: Récupération après Crash")
    print("="*80)

    batch_processor = BatchProcessor(batch_size=3)
    session_id = "test_session"

    # Vérifier s'il y a des résultats partiels
    has_pending, num_batches = batch_processor.has_pending_session(session_id)

    print(f"\n📦 Résultats partiels:")
    print(f"   - Présents: {has_pending}")
    print(f"   - Nombre de batches: {num_batches}")

    if has_pending:
        print("\n🔄 Récupération des résultats partiels possible")

        # Créer un DataFrame de test
        test_data = pd.DataFrame({
            'Adresse 1': ['Paris', 'Lille', 'Lyon', 'Marseille', 'Bordeaux'],
            'Adresse 2': ['Lyon', 'Roubaix', 'Paris', 'Nice', 'Toulouse'],
            'Distance (km)': [None] * 5
        })

        partial_df = batch_processor.get_partial_results(
            session_id,
            test_data,
            'Adresse 1',
            'Adresse 2'
        )

        if partial_df is not None:
            print(f"\n✅ {len(partial_df)} résultats partiels récupérés")
            print(partial_df[['Adresse 1', 'Adresse 2', 'Distance (km)', 'Statut']].to_string())
    else:
        print("\n✅ Aucun résultat partiel à récupérer")

    print("\n✅ Test récupération terminé")


if __name__ == "__main__":
    print("\n🚀 TESTS DES OPTIMISATIONS")
    print("="*80)

    # Test 1: Cache persistant
    test_cache_persistant()

    # Test 2: Traitement par batch
    test_batch_processing()

    # Test 3: Récupération après crash
    test_crash_recovery()

    print("\n" + "="*80)
    print("✅ TOUS LES TESTS TERMINÉS")
    print("="*80 + "\n")
