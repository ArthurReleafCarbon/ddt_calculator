"""
Test de crash réel pendant le traitement par batch
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
from calculators import BatchProcessor
from calculators.batch_distance_calculator import BatchDistanceResult
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Créer un fichier de test avec 100 lignes
test_data = pd.DataFrame({
    'Adresse 1': ['Paris', 'Lyon', 'Lille', 'Marseille', 'Bordeaux'] * 20,
    'Adresse 2': ['Lyon', 'Paris', 'Marseille', 'Lyon', 'Toulouse'] * 20,
    'Distance (km)': [None] * 100
})

print(f"📋 Fichier de test: {len(test_data)} lignes")

filename = "test_crash.xlsx"
session_id = hashlib.md5(filename.encode()).hexdigest()
print(f"🔑 Session ID: {session_id}")

batch_processor = BatchProcessor(batch_size=20)  # 20 lignes par batch = 5 batches total
api_key = os.getenv('API_ORS')

# Fonction qui va crasher après 2 batches
crash_after_items = 40
processed_count = 0

def calculate_with_crash(address1, address2, **kwargs):
    global processed_count
    processed_count += 1

    # Simuler un crash après 40 items
    if processed_count > crash_after_items:
        raise Exception("💥 SIMULATION DE CRASH !")

    # Sinon, utiliser la fonction normale
    from calculators import calculate_batch_distance
    return calculate_batch_distance(address1, address2, **kwargs)

print("\n" + "="*80)
print(f"TEST 1: Traitement qui va crasher après {crash_after_items} items")
print("="*80)

try:
    result_df, stats = batch_processor.process_batches(
        df=test_data,
        process_function=calculate_with_crash,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=lambda c, t, m: print(f"⏳ {m}: {c}/{t}"),
        max_workers=5,
        api_key_ors=api_key,
        quiet=True
    )
    print("❌ Le traitement aurait dû crasher !")
except Exception as e:
    print(f"\n✅ Crash simulé avec succès: {e}")

print("\n" + "="*80)
print("TEST 2: Vérifier les fichiers temporaires après crash")
print("="*80)

has_pending, num_batches = batch_processor.has_pending_session(session_id)
print(f"📦 Fichiers temporaires: {num_batches} batch(s)")

if has_pending:
    print(f"✅ {num_batches} batch(s) sauvegardé(s) et récupérables !")

    # Récupérer les résultats partiels
    partial_df = batch_processor.get_partial_results(session_id, test_data, 'Adresse 1', 'Adresse 2')
    calculated = len(partial_df[partial_df['Distance (km)'].notna()])
    print(f"📊 Résultats partiels: {calculated} lignes calculées sur {len(test_data)}")

    print("\n" + "="*80)
    print("TEST 3: Reprendre le calcul (sans crash cette fois)")
    print("="*80)

    # Réinitialiser le compteur de crash
    processed_count = 0
    crash_after_items = 9999  # Pas de crash cette fois

    # Reprendre
    from calculators import calculate_batch_distance
    result_df, stats = batch_processor.process_batches(
        df=test_data,
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=lambda c, t, m: print(f"⏳ {m}: {c}/{t}"),
        max_workers=5,
        api_key_ors=api_key,
        quiet=True
    )

    print(f"\n✅ Reprise terminée: {stats['success_count']} succès sur {len(test_data)} lignes")

    # Vérifier le nettoyage
    has_pending_after, num_batches_after = batch_processor.has_pending_session(session_id)
    print(f"🧹 Fichiers temporaires après reprise: {num_batches_after}")

    if num_batches_after == 0:
        print("✅ Nettoyage automatique réussi !")
    else:
        print("⚠️ Fichiers temporaires non nettoyés")

else:
    print("❌ Aucun fichier temporaire trouvé - la reprise ne fonctionnera pas !")
