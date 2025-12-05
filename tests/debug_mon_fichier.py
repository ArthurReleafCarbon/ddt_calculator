"""
Test de debug pour identifier pourquoi toutes les lignes sont "Adresse manquante"
UTILISATION: python tests/debug_mon_fichier.py /chemin/vers/ton/fichier.xlsx
"""

import sys
sys.path.insert(0, '/Users/arthurdercq/code/auto_dist_ddt')

import pandas as pd
import argparse

# Parser les arguments
parser = argparse.ArgumentParser()
parser.add_argument('file', help='Chemin vers le fichier Excel')
args = parser.parse_args()

print("="*80)
print("🔍 DEBUG: Analyse du fichier Excel")
print("="*80)

# Lire le fichier
print(f"\n📂 Lecture de: {args.file}")
df = pd.read_excel(args.file)

print(f"\n📊 Informations sur le DataFrame:")
print(f"   - Nombre de lignes: {len(df)}")
print(f"   - Nombre de colonnes: {len(df.columns)}")
print(f"   - Noms des colonnes: {df.columns.tolist()}")

print(f"\n📋 Types de données:")
print(df.dtypes)

print(f"\n👀 Aperçu des 5 premières lignes:")
print(df.head())

# Simuler l'identification des colonnes (comme dans l'app)
col_names = df.columns.tolist()
address1_col = col_names[0]
address2_col = col_names[1]
distance_col = col_names[2] if len(col_names) > 2 else "Distance (km)"

print(f"\n🎯 Colonnes identifiées:")
print(f"   - Adresse 1: '{address1_col}'")
print(f"   - Adresse 2: '{address2_col}'")
print(f"   - Distance: '{distance_col}'")

# Simuler la validation (comme dans batch_processor)
print(f"\n🔍 Validation des adresses (10 premières lignes):")
print("="*80)

invalid_values = ['nan', 'NaN', '<NA>', 'None', '', 'null', 'NULL']
valid_count = 0
invalid_count = 0

for idx, row in df.head(10).iterrows():
    address1_raw = row[address1_col]
    address2_raw = row[address2_col]

    address1 = str(address1_raw).strip()
    address2 = str(address2_raw).strip()

    is_valid = address1 not in invalid_values and address2 not in invalid_values

    status = "✅ VALIDE" if is_valid else "❌ INVALIDE"

    print(f"\nLigne {idx}: {status}")
    print(f"  Raw: {repr(address1_raw)} → {repr(address2_raw)}")
    print(f"  Après conversion: '{address1}' → '{address2}'")
    print(f"  Types: {type(address1_raw)} → {type(address2_raw)}")

    if not is_valid:
        print(f"  Raison: address1 in invalid? {address1 in invalid_values}, address2 in invalid? {address2 in invalid_values}")
        invalid_count += 1
    else:
        valid_count += 1

print(f"\n" + "="*80)
print(f"📊 Résumé (sur les 10 premières lignes):")
print(f"   ✅ Lignes valides: {valid_count}")
print(f"   ❌ Lignes invalides: {invalid_count}")

# Vérifier sur TOUT le fichier
all_valid = 0
all_invalid = 0

for idx, row in df.iterrows():
    address1 = str(row[address1_col]).strip()
    address2 = str(row[address2_col]).strip()

    if address1 not in invalid_values and address2 not in invalid_values:
        all_valid += 1
    else:
        all_invalid += 1

print(f"\n📊 Résumé (sur TOUT le fichier - {len(df)} lignes):")
print(f"   ✅ Lignes valides: {all_valid}")
print(f"   ❌ Lignes invalides: {all_invalid}")

if all_invalid == len(df):
    print(f"\n❌ PROBLÈME CRITIQUE: TOUTES les lignes sont invalides !")
    print(f"   → Vérifier les noms de colonnes")
    print(f"   → Vérifier le format des données")
    print(f"   → S'assurer que les colonnes contiennent bien des adresses")
elif all_invalid > 0:
    print(f"\n⚠️ {all_invalid} lignes invalides détectées")
    print(f"   → Ces lignes seront ignorées pendant le traitement")
else:
    print(f"\n✅ Toutes les lignes sont valides !")
