"""
Test simple du système de batch pour voir où ça bloque
"""

import pandas as pd
from calculators import BatchProcessor, calculate_batch_distance
from config import get_api_key
import time

# Créer un petit DataFrame de test
test_data = pd.DataFrame({
    'Adresse 1': ['Paris', 'Lille', 'Lyon'],
    'Adresse 2': ['Lyon', 'Roubaix', 'Paris'],
    'Distance (km)': [None, None, None]
})

print("📊 DataFrame de test:")
print(test_data)

# Créer le BatchProcessor avec un petit batch
batch_processor = BatchProcessor(batch_size=2)

api_key_ors = get_api_key()

# Callback de progression
progress_updates = []

def progress_callback(current, total, message):
    update = f"[{current}/{total}] {message}"
    print(update)
    progress_updates.append(update)

print("\n🚀 Démarrage du traitement...")
start_time = time.time()

try:
    result_df, stats = batch_processor.process_batches(
        df=test_data,
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id="test_debug",
        progress_callback=progress_callback,
        max_workers=2,
        api_key_ors=api_key_ors,
        quiet=True
    )

    elapsed_time = time.time() - start_time

    print(f"\n✅ Traitement terminé en {elapsed_time:.1f} secondes")
    print(f"\n📋 Résultats:")
    print(result_df[['Adresse 1', 'Adresse 2', 'Distance (km)', 'Statut']])

    print(f"\n📊 Statistiques:")
    print(f"   - Succès: {stats['success_count']}")
    print(f"   - Avertissements: {stats['warning_count']}")
    print(f"   - Erreurs: {stats['error_count']}")

    print(f"\n📈 Mises à jour de progression reçues: {len(progress_updates)}")
    for update in progress_updates:
        print(f"   {update}")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
