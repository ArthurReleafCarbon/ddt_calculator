"""
Debug du problème "Adresse manquante"
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
from calculators import BatchProcessor, calculate_batch_distance
import os
from dotenv import load_dotenv

load_dotenv()

# Simuler différents types de données Excel
test_cases = [
    {
        'name': 'Cas 1: Adresses normales',
        'data': pd.DataFrame({
            'Adresse 1': ['Paris', 'Lyon', 'Lille'],
            'Adresse 2': ['Lyon', 'Paris', 'Marseille'],
            'Distance (km)': [None, None, None]
        })
    },
    {
        'name': 'Cas 2: Adresses avec espaces',
        'data': pd.DataFrame({
            'Adresse 1': ['  Paris  ', '  Lyon  ', '  Lille  '],
            'Adresse 2': ['  Lyon  ', '  Paris  ', '  Marseille  '],
            'Distance (km)': [None, None, None]
        })
    },
    {
        'name': 'Cas 3: Avec cellules vides',
        'data': pd.DataFrame({
            'Adresse 1': ['Paris', '', 'Lille'],
            'Adresse 2': ['Lyon', 'Paris', ''],
            'Distance (km)': [None, None, None]
        })
    },
    {
        'name': 'Cas 4: Avec NaN pandas',
        'data': pd.DataFrame({
            'Adresse 1': ['Paris', pd.NA, 'Lille'],
            'Adresse 2': ['Lyon', 'Paris', pd.NA],
            'Distance (km)': [None, None, None]
        })
    }
]

for test_case in test_cases:
    print("\n" + "="*80)
    print(f"🧪 {test_case['name']}")
    print("="*80)

    df = test_case['data']
    print("\n📋 Données:")
    print(df)

    # Simuler ce que fait batch_processor
    print("\n🔍 Analyse de validation:")

    address1_col = 'Adresse 1'
    address2_col = 'Adresse 2'

    addresses_pairs = []
    valid_indices = []
    skipped_indices = []

    for idx, row in df.iterrows():
        address1 = str(row[address1_col]).strip()
        address2 = str(row[address2_col]).strip()

        print(f"\n  Ligne {idx}:")
        print(f"    Original: '{row[address1_col]}' → '{row[address2_col]}'")
        print(f"    Après str().strip(): '{address1}' → '{address2}'")

        # Condition actuelle
        if not address1 or address1 == "nan" or not address2 or address2 == "nan":
            print(f"    ❌ SKIPPED: address1={repr(address1)}, address2={repr(address2)}")
            print(f"       not address1: {not address1}")
            print(f"       address1 == 'nan': {address1 == 'nan'}")
            print(f"       not address2: {not address2}")
            print(f"       address2 == 'nan': {address2 == 'nan'}")
            skipped_indices.append(idx)
            continue

        print(f"    ✅ VALID")
        addresses_pairs.append((address1, address2))
        valid_indices.append(idx)

    print(f"\n📊 Résultat:")
    print(f"  ✅ Lignes valides: {len(valid_indices)} → {valid_indices}")
    print(f"  ❌ Lignes skippées: {len(skipped_indices)} → {skipped_indices}")

print("\n" + "="*80)
print("💡 DIAGNOSTIC")
print("="*80)
print("""
Si TOUTES les lignes sont skippées, les causes possibles sont:

1. Les noms de colonnes ne correspondent pas
   → Vérifier que les colonnes s'appellent bien comme attendu

2. Les données sont lues comme NaN pandas
   → Vérifier le format du fichier Excel

3. Les cellules contiennent des espaces ou caractères invisibles
   → Utiliser .strip() résout normalement ce problème

4. Le type de données est incorrect (dtype object/string)
   → Forcer la conversion en string résout normalement ce problème
""")
