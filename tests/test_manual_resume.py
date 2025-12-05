"""
Test manuel de reprise: crée des fichiers temporaires, puis simule une reprise
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
from calculators import BatchProcessor, calculate_batch_distance
import os
from dotenv import load_dotenv
import hashlib
import json
from pathlib import Path

load_dotenv()

test_data = pd.DataFrame({
    'Adresse 1': ['Paris', 'Lyon', 'Lille', 'Marseille', 'Bordeaux', 'Toulouse', 'Nice', 'Nantes'] * 10,
    'Adresse 2': ['Lyon', 'Paris', 'Marseille', 'Lyon', 'Toulouse', 'Bordeaux', 'Lyon', 'Paris'] * 10,
    'Distance (km)': [None] * 80
})

print(f"📋 Fichier de test: {len(test_data)} lignes")

filename = "test_manual_resume.xlsx"
session_id = hashlib.md5(filename.encode()).hexdigest()
print(f"🔑 Session ID: {session_id}\n")

batch_processor = BatchProcessor(batch_size=20)  # 4 batches total
api_key = os.getenv('API_ORS')

print("="*80)
print("ÉTAPE 1: Traiter seulement les 2 premiers batches (40 lignes)")
print("="*80)

# Traiter seulement 40 lignes (2 batches)
result_df, stats = batch_processor.process_batches(
    df=test_data.head(40),
    process_function=calculate_batch_distance,
    address1_col='Adresse 1',
    address2_col='Adresse 2',
    session_id=session_id,
    progress_callback=lambda c, t, m: print(f"  ⏳ {m}: {c}/{t} lignes"),
    max_workers=5,
    api_key_ors=api_key,
    quiet=True
)

print(f"\n✅ 2 batches traités: {stats['success_count']} succès")

# Vérifier les fichiers temporaires
temp_dir = Path(".cache/temp_batches")
batch_files = list(temp_dir.glob(f"{session_id}_batch_*.json"))
print(f"📦 Fichiers temporaires créés: {len(batch_files)}")

if len(batch_files) == 0:
    print("❌ PROBLÈME: Les fichiers ont été nettoyés trop tôt!")
    print("   Le système nettoie après chaque traitement réussi.")
    print("   Pour tester la reprise, il faut interrompre manuellement.")
    print("\n💡 SOLUTION: Dans l'app Streamlit, si tu fermes l'onglet pendant")
    print("   le traitement, les fichiers resteront et la reprise fonctionnera.")
else:
    for f in batch_files:
        print(f"  - {f.name}")

    print("\n" + "="*80)
    print("ÉTAPE 2: Vérifier la détection de session en attente")
    print("="*80)

    has_pending, num_batches = batch_processor.has_pending_session(session_id)
    print(f"📦 Session en attente: {has_pending}")
    print(f"📊 Nombre de batches: {num_batches}")

    if has_pending:
        print("\n" + "="*80)
        print("ÉTAPE 3: Récupérer les résultats partiels")
        print("="*80)

        partial_df = batch_processor.get_partial_results(session_id, test_data, 'Adresse 1', 'Adresse 2')
        calculated = len(partial_df[partial_df['Distance (km)'].notna()])
        print(f"✅ Résultats partiels: {calculated}/{len(test_data)} lignes calculées")

        print("\n" + "="*80)
        print("ÉTAPE 4: Reprendre le traitement (complète les 80 lignes)")
        print("="*80)

        result_df, stats = batch_processor.process_batches(
            df=test_data,  # Toutes les 80 lignes
            process_function=calculate_batch_distance,
            address1_col='Adresse 1',
            address2_col='Adresse 2',
            session_id=session_id,
            progress_callback=lambda c, t, m: print(f"  ⏳ {m}: {c}/{t} lignes"),
            max_workers=5,
            api_key_ors=api_key,
            quiet=True
        )

        print(f"\n✅ Traitement complet: {stats['success_count']} succès sur {len(test_data)} lignes")

        # Vérifier le nettoyage
        has_pending_after, num_batches_after = batch_processor.has_pending_session(session_id)
        print(f"🧹 Fichiers temporaires après reprise: {num_batches_after}")

        if num_batches_after == 0:
            print("✅ Nettoyage automatique réussi !")
        else:
            print("⚠️ Fichiers non nettoyés")
