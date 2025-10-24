import requests
import time
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

def normalize_commune_name(commune):
    """Normalise le nom de commune pour améliorer la recherche et la comparaison"""
    if not commune or str(commune).strip() == "" or str(commune).lower() == "nan":
        return None

    # Convertir en majuscules et supprimer les espaces en début/fin
    commune = str(commune).upper().strip()

    # Supprimer les multiples espaces
    commune = " ".join(commune.split())

    # Gestion complète des variations de SAINT
    # Remplacer toutes les variations par SAINT-
    import re

    # Pattern pour capturer ST, St, st suivi d'un espace ou d'un tiret
    commune = re.sub(r'\bST[\s\-]+', 'SAINT-', commune)
    commune = re.sub(r'\bSAINT\s+', 'SAINT-', commune)

    # Supprimer les mentions CEDEX avec ou sans numéro
    commune = re.sub(r'\s*CEDEX\s*\d*', '', commune)

    # Supprimer les tirets multiples et normaliser
    commune = re.sub(r'-+', '-', commune)

    # Supprimer les espaces avant/après les tirets
    commune = re.sub(r'\s*-\s*', '-', commune)

    # Nettoyer les espaces multiples résultants
    commune = " ".join(commune.split()).strip()

    return commune if commune else None

def get_coordinates_nominatim(commune, region=None):
    """Récupère les coordonnées d'une commune via Nominatim (gratuit)"""
    try:
        geolocator = Nominatim(user_agent="ddt_calculator")

        # Recherche avec région si spécifiée
        if region:
            location = geolocator.geocode(
                f"{commune}, {region}, France",
                timeout=10
            )
            if location:
                return (location.latitude, location.longitude)

        # Recherche en France
        location = geolocator.geocode(f"{commune}, France", timeout=10)
        if location:
            return (location.latitude, location.longitude)

        return None
    except Exception as e:
        print(f"Erreur Nominatim pour {commune}: {str(e)}")
        return None

def get_coordinates_ors(commune, api_key, region=None):
    """Récupère les coordonnées via OpenRouteService"""
    try:
        url = "https://api.openrouteservice.org/geocode/search"
        search_text = f"{commune}, {region}, France" if region else f"{commune}, France"
        params = {
            "api_key": api_key,
            "text": search_text,
            "boundary.country": "FR",
            "size": 1
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("features"):
                coords = data["features"][0]["geometry"]["coordinates"]
                return (coords[1], coords[0])  # lat, lon

        return None
    except Exception as e:
        print(f"Erreur ORS pour {commune}: {str(e)}")
        return None

def get_coordinates_google(commune, api_key, region=None):
    """Récupère les coordonnées via Google Maps Geocoding API"""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        address = f"{commune}, {region}, France" if region else f"{commune}, France"
        params = {
            "address": address,
            "key": api_key
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                return (location["lat"], location["lng"])

        return None
    except Exception as e:
        print(f"Erreur Google Maps pour {commune}: {str(e)}")
        return None

def calculate_distance(commune1, commune2, api_choice="Nominatim (Gratuit)", api_key=None, region1=None, region2=None):
    """
    Calcule la distance en kilomètres entre deux communes en France

    Args:
        commune1: Commune de départ
        commune2: Commune d'arrivée
        api_choice: Service à utiliser ("Nominatim (Gratuit)", "OpenRouteService", "Google Maps")
        api_key: Clé API si nécessaire
        region1: Région/département de la commune1 (optionnel, améliore la précision)
        region2: Région/département de la commune2 (optionnel, améliore la précision)

    Returns:
        Distance en km ou None si erreur
    """

    # Normalisation des noms
    commune1_normalized = normalize_commune_name(commune1)
    commune2_normalized = normalize_commune_name(commune2)

    # Logs de débogage
    print(f"\n=== Calcul de distance ===")
    print(f"Commune 1 (originale): '{commune1}'")
    print(f"Commune 1 (normalisée): '{commune1_normalized}'")
    print(f"Commune 2 (originale): '{commune2}'")
    print(f"Commune 2 (normalisée): '{commune2_normalized}'")

    # Vérifier si les communes sont valides
    if not commune1_normalized or not commune2_normalized:
        print(f"❌ Commune invalide détectée")
        return None

    # Si mêmes communes (comparaison insensible à la casse et aux espaces), distance = 0
    if commune1_normalized == commune2_normalized:
        print(f"✅ Communes identiques détectées → Distance = 0 km")
        return 0.0

    print(f"➡️  Communes différentes, calcul de la distance...")

    # Récupération des coordonnées selon l'API choisie
    coords1 = None
    coords2 = None

    if api_choice == "Nominatim (Gratuit)":
        coords1 = get_coordinates_nominatim(commune1_normalized, region1)
        time.sleep(1)  # Respect du rate limit Nominatim
        coords2 = get_coordinates_nominatim(commune2_normalized, region2)
        time.sleep(1)

    elif api_choice == "OpenRouteService":
        if not api_key:
            print("Clé API OpenRouteService manquante")
            return None
        coords1 = get_coordinates_ors(commune1_normalized, api_key, region1)
        coords2 = get_coordinates_ors(commune2_normalized, api_key, region2)

    elif api_choice == "Google Maps":
        if not api_key:
            print("Clé API Google Maps manquante")
            return None
        coords1 = get_coordinates_google(commune1_normalized, api_key, region1)
        coords2 = get_coordinates_google(commune2_normalized, api_key, region2)

    # Vérification que les coordonnées ont été trouvées
    if coords1 is None or coords2 is None:
        print(f"❌ Impossible de géolocaliser: {commune1_normalized} ou {commune2_normalized}")
        return None

    # Calcul de la distance géodésique (à vol d'oiseau)
    distance = geodesic(coords1, coords2).kilometers
    print(f"📏 Distance à vol d'oiseau: {distance:.2f} km")

    # Si la distance est très petite (< 1km), considérer que c'est la même commune
    if distance < 1.0:
        print(f"✅ Distance < 1km → Considéré comme même commune → Distance = 0 km")
        return 0.0

    # Facteur de correction pour obtenir distance routière approximative
    # (à vol d'oiseau * 1.3 est une estimation commune)
    distance_routiere = distance * 1.3
    print(f"🚗 Distance routière estimée: {distance_routiere:.2f} km")

    return distance_routiere

if __name__ == "__main__":
    # Test du module avec exemples de différentes régions
    print("Test du calculateur de distance:")

    # Exemples La Réunion
    distance = calculate_distance("LE TAMPON", "SAINT-PIERRE", region1="La Réunion", region2="La Réunion")
    if distance:
        print(f"Distance LE TAMPON → SAINT-PIERRE (Réunion): {distance:.2f} km")

    # Exemples France métropolitaine
    distance = calculate_distance("PARIS", "LYON")
    if distance:
        print(f"Distance PARIS → LYON: {distance:.2f} km")

    distance = calculate_distance("MARSEILLE", "TOULOUSE")
    if distance:
        print(f"Distance MARSEILLE → TOULOUSE: {distance:.2f} km")