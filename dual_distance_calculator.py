"""
Module de calcul de distance avec validation croisée entre Nominatim et OpenRouteService.
Ce module calcule les distances avec les deux services en parallèle et sélectionne
la valeur la plus réaliste selon des critères de validation.
"""

import logging
import time
from typing import Optional, Tuple, Dict
from distance_calculator import (
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

# Constantes de validation
MIN_DISTANCE_KM = 0
MAX_DISTANCE_KM = 300
DIFF_THRESHOLD_PERCENT = 10
ROAD_FACTOR = 1.3  # Facteur pour estimer la distance routière


class DistanceValidationResult:
    """Résultat de la validation croisée des distances"""

    def __init__(self,
                 final_distance: Optional[float],
                 nominatim_distance: Optional[float],
                 ors_distance: Optional[float],
                 source: str,
                 status: str,
                 message: str):
        self.final_distance = final_distance
        self.nominatim_distance = nominatim_distance
        self.ors_distance = ors_distance
        self.source = source
        self.status = status
        self.message = message

    def __repr__(self):
        return (f"DistanceValidationResult(final={self.final_distance}, "
                f"nominatim={self.nominatim_distance}, ors={self.ors_distance}, "
                f"source={self.source}, status={self.status})")


def is_valid_distance(distance: Optional[float]) -> bool:
    """
    Vérifie si une distance est valide selon les critères définis

    Args:
        distance: Distance en km

    Returns:
        True si la distance est valide, False sinon
    """
    if distance is None:
        return False

    return MIN_DISTANCE_KM <= distance <= MAX_DISTANCE_KM


def calculate_distance_with_service(commune1: str,
                                    commune2: str,
                                    service: str,
                                    api_key: Optional[str] = None,
                                    region1: Optional[str] = None,
                                    region2: Optional[str] = None) -> Optional[float]:
    """
    Calcule la distance entre deux communes avec un service spécifique

    Args:
        commune1: Commune de départ
        commune2: Commune d'arrivée
        service: "nominatim" ou "ors"
        api_key: Clé API pour ORS
        region1: Région de la commune 1
        region2: Région de la commune 2

    Returns:
        Distance en km ou None si erreur
    """
    # Normalisation
    commune1_norm = normalize_commune_name(commune1)
    commune2_norm = normalize_commune_name(commune2)

    if not commune1_norm or not commune2_norm:
        return None

    # Si communes identiques
    if commune1_norm == commune2_norm:
        return 0.0

    try:
        # Récupération des coordonnées
        coords1 = None
        coords2 = None

        if service == "nominatim":
            coords1 = get_coordinates_nominatim(commune1_norm, region1)
            time.sleep(1)  # Rate limit
            coords2 = get_coordinates_nominatim(commune2_norm, region2)
            time.sleep(1)

        elif service == "ors":
            if not api_key:
                logger.warning("Clé API ORS manquante")
                return None
            coords1 = get_coordinates_ors(commune1_norm, api_key, region1)
            coords2 = get_coordinates_ors(commune2_norm, api_key, region2)

        if coords1 is None or coords2 is None:
            return None

        # Calcul de la distance
        distance = geodesic(coords1, coords2).kilometers

        # Si distance très petite, considérer comme 0
        if distance < 1.0:
            return 0.0

        # Appliquer facteur routier
        distance_routiere = distance * ROAD_FACTOR

        return round(distance_routiere, 2)

    except Exception as e:
        logger.error(f"Erreur calcul {service} pour {commune1_norm} -> {commune2_norm}: {str(e)}")
        return None


def calculate_distance_dual_validation(commune1: str,
                                       commune2: str,
                                       api_key_ors: Optional[str] = None,
                                       region1: Optional[str] = None,
                                       region2: Optional[str] = None) -> DistanceValidationResult:
    """
    Calcule la distance entre deux communes avec validation croisée Nominatim + ORS

    Logique de sélection :
    1. Exclure les distances > 300 km (aberrantes)
    2. Si les deux sont valides et différence < 10% : prendre la moyenne
    3. Si une seule est valide : la prendre
    4. Si les deux sont aberrantes ou invalides : marquer "À vérifier"

    Args:
        commune1: Commune de départ
        commune2: Commune d'arrivée
        api_key_ors: Clé API OpenRouteService
        region1: Région de la commune 1
        region2: Région de la commune 2

    Returns:
        DistanceValidationResult avec la distance finale et les détails
    """
    commune1_norm = normalize_commune_name(commune1)
    commune2_norm = normalize_commune_name(commune2)

    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 CALCUL DUAL: {commune1_norm} → {commune2_norm}")
    logger.info(f"{'='*80}")

    # Calcul avec les deux services
    logger.info("📡 Calcul avec Nominatim...")
    dist_nominatim = calculate_distance_with_service(
        commune1, commune2, "nominatim", region1=region1, region2=region2
    )

    logger.info("📡 Calcul avec OpenRouteService...")
    dist_ors = calculate_distance_with_service(
        commune1, commune2, "ors", api_key_ors, region1, region2
    )

    logger.info(f"📊 Résultats bruts:")
    logger.info(f"   - Nominatim: {dist_nominatim} km")
    logger.info(f"   - ORS: {dist_ors} km")

    # Validation des distances
    nominatim_valid = is_valid_distance(dist_nominatim)
    ors_valid = is_valid_distance(dist_ors)

    logger.info(f"✓ Validation:")
    logger.info(f"   - Nominatim valide: {nominatim_valid}")
    logger.info(f"   - ORS valide: {ors_valid}")

    # Logique de sélection
    final_distance = None
    source = "none"
    status = "error"
    message = ""

    # Cas 1: Les deux sont valides
    if nominatim_valid and ors_valid:
        # Calculer la différence en pourcentage
        if dist_nominatim == 0 and dist_ors == 0:
            final_distance = 0.0
            source = "both"
            status = "ok"
            message = "Même commune détectée par les deux services"
            logger.info(f"✅ Les deux services confirment: même commune (0 km)")

        elif dist_nominatim == 0 or dist_ors == 0:
            # Un des deux est 0, l'autre non : prendre le non-zéro
            final_distance = max(dist_nominatim, dist_ors)
            source = "nominatim" if dist_nominatim > 0 else "ors"
            status = "ok"
            message = f"Une distance nulle détectée, prise de la distance non-nulle ({source})"
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
                # Différence importante : prendre la plus petite (généralement plus réaliste)
                final_distance = min(dist_nominatim, dist_ors)
                source = "nominatim" if dist_nominatim < dist_ors else "ors"
                status = "warning"
                message = f"Différence importante ({diff_percent:.1f}%), prise de la plus petite valeur ({source})"
                logger.warning(f"⚠️ Différence importante ({diff_percent:.1f}%), prise du minimum: {final_distance} km ({source})")

    # Cas 2: Seulement Nominatim est valide
    elif nominatim_valid and not ors_valid:
        final_distance = dist_nominatim
        source = "nominatim"
        status = "ok"
        message = "Seul Nominatim a fourni une distance valide"
        logger.info(f"✅ Seul Nominatim valide: {final_distance} km")

    # Cas 3: Seulement ORS est valide
    elif not nominatim_valid and ors_valid:
        final_distance = dist_ors
        source = "ors"
        status = "ok"
        message = "Seul ORS a fourni une distance valide"
        logger.info(f"✅ Seul ORS valide: {final_distance} km")

    # Cas 4: Aucun n'est valide
    else:
        final_distance = None
        source = "none"
        status = "error"
        message = "Aucune distance valide trouvée (> 300 km ou erreur)"
        logger.error(f"❌ Aucune distance valide - À VÉRIFIER MANUELLEMENT")

    result = DistanceValidationResult(
        final_distance=final_distance,
        nominatim_distance=dist_nominatim,
        ors_distance=dist_ors,
        source=source,
        status=status,
        message=message
    )

    logger.info(f"🎯 DÉCISION FINALE: {final_distance} km (source: {source}, status: {status})")
    logger.info(f"💬 Message: {message}")
    logger.info(f"{'='*80}\n")

    return result


if __name__ == "__main__":
    """Tests du module"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("API_ORS")

    if not api_key:
        logger.warning("Clé API ORS non trouvée dans .env, certains tests échoueront")

    # Test 1: Même commune
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Même commune")
    logger.info("="*80)
    result = calculate_distance_dual_validation("LILLE", "LILLE", api_key)
    print(f"Résultat: {result}")

    # Test 2: Courte distance
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Courte distance")
    logger.info("="*80)
    result = calculate_distance_dual_validation("LILLE", "ROUBAIX", api_key, region1="Nord", region2="Nord")
    print(f"Résultat: {result}")

    # Test 3: Distance moyenne
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Distance moyenne")
    logger.info("="*80)
    result = calculate_distance_dual_validation("PARIS", "LYON", api_key)
    print(f"Résultat: {result}")

    # Test 4: Longue distance (potentiellement aberrante)
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Longue distance")
    logger.info("="*80)
    result = calculate_distance_dual_validation("LILLE", "MARSEILLE", api_key)
    print(f"Résultat: {result}")
