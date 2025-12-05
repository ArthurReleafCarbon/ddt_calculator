"""
Test de la reprise de batch après crash
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
from calculators import BatchProcessor, calculate_batch_distance
import os
from dotenv import load_dotenv
import hashlib

load_dotenv()

# Créer un fichier de test
test_data = pd.DataFrame({
    'Adresse 1': ['Paris', 'Lyon', 'Lille', 'Marseille', 'Bordeaux', 'Toulouse'] * 20,  # 120 lignes
    'Adresse 2': ['Lyon', 'Paris', 'Marseille', 'Lyon', 'Toulouse', 'Bordeaux'] * 20,
    'Distance (km)': [None] * 120
})

print(f"📋 Fichier de test: {len(test_data)} lignes")

# Simuler un session_id
filename = "test_batch.xlsx"
session_id = hashlib.md5(filename.encode()).hexdigest()
print(f"🔑 Session ID: {session_id}")

# Initialiser le batch processor
batch_processor = BatchProcessor(batch_size=25)  # 25 lignes par batch = 5 batches

api_key = os.getenv('API_ORS')

# Callback pour voir la progression
def show_progress(current, total, message):
    print(f"⏳ {message}: {current}/{total} lignes ({current/total*100:.1f}%)")

print("\n" + "="*80)
print("TEST 1: Traitement complet (simuler crash après 2 batches)")
print("="*80)

try:
    # On va arrêter après 2 batches pour simuler un crash
    result_df, stats = batch_processor.process_batches(
        df=test_data.head(50),  # Seulement 50 lignes = 2 batches
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=show_progress,
        max_workers=5,
        api_key_ors=api_key,
        quiet=True
    )

    print(f"\n✅ 2 batches traités: {stats['success_count']} succès, {stats['error_count']} erreurs")

except Exception as e:
    print(f"❌ Erreur: {e}")

print("\n" + "="*80)
print("TEST 2: Vérifier les fichiers temporaires")
print("="*80)

has_pending, num_batches = batch_processor.has_pending_session(session_id)
print(f"📦 Fichiers temporaires trouvés: {num_batches} batch(s)")

if has_pending:
    print("✅ Reprise possible !")

    # Récupérer les résultats partiels
    partial_df = batch_processor.get_partial_results(session_id, test_data, 'Adresse 1', 'Adresse 2')
    print(f"📊 Résultats partiels: {len(partial_df[partial_df['Distance (km)'].notna()])} lignes calculées")

    print("\n" + "="*80)
    print("TEST 3: Reprendre le calcul (compléter les 120 lignes)")
    print("="*80)

    # Reprendre avec TOUTES les lignes
    result_df, stats = batch_processor.process_batches(
        df=test_data,  # Toutes les 120 lignes
        process_function=calculate_batch_distance,
        address1_col='Adresse 1',
        address2_col='Adresse 2',
        session_id=session_id,
        progress_callback=show_progress,
        max_workers=5,
        api_key_ors=api_key,
        quiet=True
    )

    print(f"\n✅ Traitement complet: {stats['success_count']} succès, {stats['error_count']} erreurs")
    print(f"📈 Total de lignes traitées: {len(result_df)}")

    # Vérifier qu'il n'y a plus de fichiers temporaires
    has_pending_after, num_batches_after = batch_processor.has_pending_session(session_id)
    print(f"\n🧹 Fichiers temporaires après reprise: {num_batches_after}")
    if num_batches_after == 0:
        print("✅ Nettoyage automatique réussi !")
    else:
        print("⚠️ Fichiers temporaires non supprimés")

else:
    print("❌ Pas de reprise possible")
