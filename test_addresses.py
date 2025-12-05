"""
Test avec les adresses fournies par l'utilisateur
"""

import pandas as pd
from calculators import calculate_batch_distance
from config import get_api_key
import time

# Adresses de test
test_addresses = [
    ("35 Rue Winston Churchill, 59160 Lille", "LE PUY EN VELAY"),
    ("35 Rue Winston Churchill, 59160 Lille", "MUNDOLSHEIM"),
    ("35 Rue Winston Churchill, 59160 Lille", "PRAGUE - Czech Republic, 25,9"),
    ("35 Rue Winston Churchill, 59160 Lille", "SAINTES"),
    ("35 Rue Winston Churchill, 59160 Lille", "LA LOUVIERE, Belgique"),
    ("35 Rue Winston Churchill, 59160 Lille", "BRECE"),
    ("35 Rue Winston Churchill, 59160 Lille", "RENNES, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "ROMILLY SUR ANDELLE, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "Val de Reuil"),
    ("35 Rue Winston Churchill, 59160 Lille", "AVIGNON"),
    ("35 Rue Winston Churchill, 59160 Lille", "BRUGES, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "BEAUCOUZE, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "ESCALQUENS, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "NIMES"),
    ("35 Rue Winston Churchill, 59160 Lille", "ROANNE, France"),
    ("35 Rue Winston Churchill, 59160 Lille", "Nimes Cedex 9, France"),
]

print("🧪 TEST DES ADRESSES UTILISATEUR")
print("=" * 80)

api_key = get_api_key()

for i, (addr1, addr2) in enumerate(test_addresses, 1):
    print(f"\n[{i}/{len(test_addresses)}] Test: {addr1} → {addr2}")
    print("-" * 80)

    try:
        result = calculate_batch_distance(
            addr1,
            addr2,
            api_key_ors=api_key,
            quiet=False
        )

        print(f"✅ Distance: {result.final_distance} km")
        print(f"   Status: {result.status}")
        print(f"   Source: {result.source}")
        print(f"   Message: {result.message}")
        print(f"   Nominatim: {result.nominatim_distance} km")
        print(f"   ORS: {result.ors_distance} km")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    # Pause pour éviter le rate limiting
    if i < len(test_addresses):
        print("\n⏳ Pause de 2 secondes...")
        time.sleep(2)

print("\n" + "=" * 80)
print("✅ TESTS TERMINÉS")
