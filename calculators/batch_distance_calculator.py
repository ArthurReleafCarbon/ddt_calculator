"""
Module de calcul de distances par lots entre paires d'adresses.
Utilise le système de validation croisée Nominatim + ORS sans plafond de distance.
"""

import logging
import time
from typing import Optional, List, Tuple
from .distance_calculator import (
    normalize_commune_name,
    get_coordinates_nominatim,
    get_coordinates_ors
)
from geopy.distance import geodesic

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constantes de validation (sans plafond de distance)
DIFF_THRESHOLD_PERCENT = 10
ROAD_FACTOR = 1.3  # Facteur pour estimer la distance routière


class BatchDistanceResult:
    """Résultat du calcul de distance pour un lot"""

    def __init__(self,
                 final_distance: Optional[float],
                 nominatim_distance: Optional[float],
                 ors_distance: Optional[float],
                 source: str,
                 status: str,
                 message: str,
                 address1: str,
                 address2: str):
        self.final_distance = final_distance
        self.nominatim_distance = nominatim_distance
        self.ors_distance = ors_distance
        self.source = source
        self.status = status
        self.message = message
        self.address1 = address1
        self.address2 = address2

    def __repr__(self):
        return (f"BatchDistanceResult({self.address1} -> {self.address2}, "
                f"distance={self.final_distance} km, source={self.source})")


def calculate_batch_distance(address1: str,
                              address2: str,
                              api_key_ors: Optional[str] = None,
                              region1: Optional[str] = None,
                              region2: Optional[str] = None) -> BatchDistanceResult:
    """
    Calcule la distance entre deux adresses avec validation croisée Nominatim + ORS
    SANS plafond de distance (adapté pour les longues distances)

    Logique de sélection :
    1. Si les deux services retournent une valeur et différence < 10% : prendre la moyenne
    2. Si les deux services retournent une valeur et différence > 10% : prendre la plus petite (généralement plus réaliste)
    3. Si un seul service retourne une valeur : la prendre
    4. Si aucun service ne retourne de valeur : marquer "À vérifier"

    Args:
        address1: Première adresse (format libre)
        address2: Deuxième adresse (format libre)
        api_key_ors: Clé API OpenRouteService
        region1: Région de l'adresse 1 (optionnel)
        region2: Région de l'adresse 2 (optionnel)

    Returns:
        BatchDistanceResult avec la distance finale et les détails
    """
    address1_norm = normalize_commune_name(address1)
    address2_norm = normalize_commune_name(address2)

    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 CALCUL BATCH: {address1_norm} → {address2_norm}")
    logger.info(f"{'='*80}")

    # Si adresses identiques
    if address1_norm == address2_norm:
        logger.info(f"✅ Même adresse détectée: 0 km")
        return BatchDistanceResult(
            final_distance=0.0,
            nominatim_distance=0.0,
            ors_distance=0.0,
            source="both",
            status="ok",
            message="Même adresse détectée",
            address1=address1,
            address2=address2
        )

    # Calcul avec Nominatim
    logger.info("📡 Calcul avec Nominatim...")
    dist_nominatim = _calculate_with_nominatim(address1_norm, address2_norm, region1, region2)

    # Calcul avec ORS (si clé disponible)
    dist_ors = None
    if api_key_ors:
        logger.info("📡 Calcul avec OpenRouteService...")
        dist_ors = _calculate_with_ors(address1_norm, address2_norm, api_key_ors, region1, region2)

    logger.info(f"📊 Résultats bruts:")
    logger.info(f"   - Nominatim: {dist_nominatim} km")
    logger.info(f"   - ORS: {dist_ors} km")

    # Logique de sélection (sans validation de plafond de distance)
    final_distance = None
    source = "none"
    status = "error"
    message = ""

    # Les deux services ont retourné une valeur
    if dist_nominatim is not None and dist_ors is not None:
        # Calculer la différence en pourcentage
        if dist_nominatim == 0 and dist_ors == 0:
            final_distance = 0.0
            source = "both"
            status = "ok"
            message = "Même adresse confirmée par les deux services"
            logger.info(f"✅ Même adresse confirmée: 0 km")

        elif dist_nominatim == 0 or dist_ors == 0:
            # Un des deux est 0, l'autre non : prendre le non-zéro
            final_distance = max(dist_nominatim, dist_ors)
            source = "nominatim" if dist_nominatim > 0 else "ors"
            status = "ok"
            message = f"Distance nulle sur un service, prise de {source}"
            logger.info(f"⚠️ Distance nulle sur un service, prise de {source}: {final_distance} km")

        else:
            # Les deux sont non-nulles : calculer la différence
            diff_percent = abs(dist_nominatim - dist_ors) / max(dist_nominatim, dist_ors) * 100
            logger.info(f"📐 Différence: {diff_percent:.2f}%")

            if diff_percent < DIFF_THRESHOLD_PERCENT:
                final_distance = round((dist_nominatim + dist_ors) / 2, 2)
                source = "average"
                status = "ok"
                message = f"Différence < {DIFF_THRESHOLD_PERCENT}%, moyenne prise"
                logger.info(f"✅ Différence acceptable, moyenne: {final_distance} km")
            else:
                # Différence importante : prendre la plus petite
                final_distance = min(dist_nominatim, dist_ors)
                source = "nominatim" if dist_nominatim < dist_ors else "ors"
                status = "warning"
                message = f"Différence importante ({diff_percent:.1f}%), prise de la plus petite valeur ({source})"
                logger.warning(f"⚠️ Différence importante ({diff_percent:.1f}%), prise du minimum: {final_distance} km ({source})")

    # Seulement Nominatim a retourné une valeur
    elif dist_nominatim is not None:
        final_distance = dist_nominatim
        source = "nominatim"
        status = "ok"
        message = "Seul Nominatim a fourni une distance"
        logger.info(f"✅ Seul Nominatim valide: {final_distance} km")

    # Seulement ORS a retourné une valeur
    elif dist_ors is not None:
        final_distance = dist_ors
        source = "ors"
        status = "ok"
        message = "Seul ORS a fourni une distance"
        logger.info(f"✅ Seul ORS valide: {final_distance} km")

    # Aucun service n'a retourné de valeur
    else:
        final_distance = None
        source = "none"
        status = "error"
        message = "Aucune distance calculable (erreur de géolocalisation)"
        logger.error(f"❌ Aucune distance calculable - À VÉRIFIER MANUELLEMENT")

    result = BatchDistanceResult(
        final_distance=final_distance,
        nominatim_distance=dist_nominatim,
        ors_distance=dist_ors,
        source=source,
        status=status,
        message=message,
        address1=address1,
        address2=address2
    )

    logger.info(f"🎯 DÉCISION FINALE: {final_distance} km (source: {source}, status: {status})")
    logger.info(f"💬 Message: {message}")
    logger.info(f"{'='*80}\n")

    return result


def _calculate_with_nominatim(address1: str,
                               address2: str,
                               region1: Optional[str] = None,
                               region2: Optional[str] = None) -> Optional[float]:
    """Calcule la distance avec Nominatim"""
    try:
        coords1 = get_coordinates_nominatim(address1, region1)
        time.sleep(1)  # Rate limit
        coords2 = get_coordinates_nominatim(address2, region2)
        time.sleep(1)

        if coords1 is None or coords2 is None:
            return None

        distance = geodesic(coords1, coords2).kilometers

        # Si distance très petite, considérer comme 0
        if distance < 1.0:
            return 0.0

        # Appliquer facteur routier
        distance_routiere = distance * ROAD_FACTOR

        return round(distance_routiere, 2)

    except Exception as e:
        logger.error(f"Erreur calcul Nominatim pour {address1} -> {address2}: {str(e)}")
        return None


def _calculate_with_ors(address1: str,
                        address2: str,
                        api_key: str,
                        region1: Optional[str] = None,
                        region2: Optional[str] = None) -> Optional[float]:
    """Calcule la distance avec OpenRouteService"""
    try:
        coords1 = get_coordinates_ors(address1, api_key, region1)
        coords2 = get_coordinates_ors(address2, api_key, region2)

        if coords1 is None or coords2 is None:
            return None

        distance = geodesic(coords1, coords2).kilometers

        # Si distance très petite, considérer comme 0
        if distance < 1.0:
            return 0.0

        # Appliquer facteur routier
        distance_routiere = distance * ROAD_FACTOR

        return round(distance_routiere, 2)

    except Exception as e:
        logger.error(f"Erreur calcul ORS pour {address1} -> {address2}: {str(e)}")
        return None


if __name__ == "__main__":
    """Tests du module"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("API_ORS")

    if not api_key:
        logger.warning("Clé API ORS non trouvée dans .env")

    # Test 1: Courte distance
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Courte distance (même région)")
    logger.info("="*80)
    result = calculate_batch_distance("Lille", "Roubaix", api_key)
    print(f"Résultat: {result}")

    # Test 2: Moyenne distance
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Moyenne distance")
    logger.info("="*80)
    result = calculate_batch_distance("Paris", "Lyon", api_key)
    print(f"Résultat: {result}")

    # Test 3: Longue distance (sans plafond)
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Longue distance (sans plafond)")
    logger.info("="*80)
    result = calculate_batch_distance("Lille", "Marseille", api_key)
    print(f"Résultat: {result}")

    # Test 4: Très longue distance
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Très longue distance")
    logger.info("="*80)
    result = calculate_batch_distance("Paris", "Nice", api_key)
    print(f"Résultat: {result}")
