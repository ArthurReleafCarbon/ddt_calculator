"""
Test direct de l'API OpenRouteService
"""

import requests
from config import get_api_key

api_key = get_api_key()

if not api_key:
    print("❌ Pas de clé API ORS trouvée")
    exit(1)

print(f"✅ Clé API trouvée: {api_key[:10]}...")

# Test 1: Adresse française simple
print("\n" + "="*80)
print("TEST 1: Lille, France")
print("="*80)

url = "https://api.openrouteservice.org/geocode/search"
params = {
    "api_key": api_key,
    "text": "35 Rue Winston Churchill, 59160 Lille, France",
    "boundary.country": "FR",
    "size": 1
}

response = requests.get(url, params=params, timeout=10)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Features trouvées: {len(data.get('features', []))}")
    if data.get("features"):
        coords = data["features"][0]["geometry"]["coordinates"]
        print(f"Coordonnées: lat={coords[1]}, lon={coords[0]}")
else:
    print(f"Erreur: {response.text}")

# Test 2: Adresse française (RENNES)
print("\n" + "="*80)
print("TEST 2: RENNES, France (sans boundary.country)")
print("="*80)

params2 = {
    "api_key": api_key,
    "text": "RENNES, France",
    "size": 1
}

response2 = requests.get(url, params=params2, timeout=10)
print(f"Status: {response2.status_code}")

if response2.status_code == 200:
    data2 = response2.json()
    print(f"Features trouvées: {len(data2.get('features', []))}")
    if data2.get("features"):
        coords2 = data2["features"][0]["geometry"]["coordinates"]
        print(f"Coordonnées: lat={coords2[1]}, lon={coords2[0]}")
        print(f"Label: {data2['features'][0]['properties'].get('label', 'N/A')}")
else:
    print(f"Erreur: {response2.text}")

# Test 3: Belgique
print("\n" + "="*80)
print("TEST 3: LA LOUVIERE, Belgique")
print("="*80)

params3 = {
    "api_key": api_key,
    "text": "LA LOUVIERE, Belgique",
    "size": 1
}

response3 = requests.get(url, params=params3, timeout=10)
print(f"Status: {response3.status_code}")

if response3.status_code == 200:
    data3 = response3.json()
    print(f"Features trouvées: {len(data3.get('features', []))}")
    if data3.get("features"):
        coords3 = data3["features"][0]["geometry"]["coordinates"]
        print(f"Coordonnées: lat={coords3[1]}, lon={coords3[0]}")
        print(f"Label: {data3['features'][0]['properties'].get('label', 'N/A')}")
    else:
        print("Aucune feature trouvée")
else:
    print(f"Erreur: {response3.text}")
