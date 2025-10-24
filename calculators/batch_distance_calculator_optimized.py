"""
Module de calcul de distances par lots OPTIMISÉ
- Cache des géolocalisations pour éviter les appels répétés
- Parallélisation des calculs avec ThreadPoolExecutor
- Mode quiet pour réduire le logging sur gros fichiers
"""

import logging
import time
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from .distance_calculator import (
    normalize_commune_name,
    get_coordinates_nominatim,
    get_coordinates_ors
)
from geopy.distance import geodesic
from .geocoding_cache import get_cache
from .batch_distance_calculator import BatchDistanceResult

# Configuration du logging
logger = logging.getLogger(__name__)

# Constantes
DIFF_THRESHOLD_PERCENT = 10
ROAD_FACTOR = 1.3
MAX_WORKERS = 5  # Nombre de threads parallèles


def get_coordinates_nominatim_cached(address: str, region: Optional[str] = None) -> Optional[tuple]:
    """Géolocalisation Nominatim avec cache"""
    cache = get_cache()

    # Vérifier le cache d'abord
    coords = cache.get(address, "nominatim", region)
    if coords is not None:
        return coords

    # Sinon, faire l'appel API
    coords = get_coordinates_nominatim(address, region)

    # Stocker dans le cache
    cache.set(address, "nominatim", coords, region)

    # Rate limit uniquement si pas de cache
    time.sleep(1)

    return coords


def get_coordinates_ors_cached(address: str, api_key: str, region: Optional[str] = None) -> Optional[tuple]:
    """Géolocalisation ORS avec cache"""
    cache = get_cache()

    # Vérifier le cache d'abord
    coords = cache.get(address, "ors", region)
    if coords is not None:
        return coords

    # Sinon, faire l'appel API
    coords = get_coordinates_ors(address, api_key, region)

    # Stocker dans le cache
    cache.set(address, "ors", coords, region)

    return coords


def calculate_batch_distance(address1: str,
                              address2: str,
                              api_key_ors: Optional[str] = None,
                              region1: Optional[str] = None,
                              region2: Optional[str] = None,
                              quiet: bool = False) -> BatchDistanceResult:
    """
    Calcule la distance entre deux adresses avec validation croisée Nominatim + ORS
    Version OPTIMISÉE avec cache

    Args:
        address1: Première adresse
        address2: Deuxième adresse
        api_key_ors: Clé API OpenRouteService
        region1: Région de l'adresse 1 (optionnel)
        region2: Région de l'adresse 2 (optionnel)
        quiet: Mode silencieux (réduit les logs)

    Returns:
        BatchDistanceResult avec la distance finale
    """
    address1_norm = normalize_commune_name(address1)
    address2_norm = normalize_commune_name(address2)

    if not quiet:
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 CALCUL BATCH: {address1_norm} → {address2_norm}")
        logger.info(f"{'='*80}")

    # Si adresses identiques
    if address1_norm == address2_norm:
        if not quiet:
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

    # Calcul avec Nominatim (avec cache)
    if not quiet:
        logger.info("📡 Calcul avec Nominatim...")
    dist_nominatim = _calculate_with_nominatim_cached(address1_norm, address2_norm, region1, region2, quiet)

    # Calcul avec ORS (si clé disponible, avec cache)
    dist_ors = None
    if api_key_ors:
        if not quiet:
            logger.info("📡 Calcul avec OpenRouteService...")
        dist_ors = _calculate_with_ors_cached(address1_norm, address2_norm, api_key_ors, region1, region2, quiet)

    if not quiet:
        logger.info(f"📊 Résultats bruts:")
        logger.info(f"   - Nominatim: {dist_nominatim} km")
        logger.info(f"   - ORS: {dist_ors} km")

    # Logique de sélection (identique à la version originale)
    final_distance = None
    source = "none"
    status = "error"
    message = ""

    # Les deux services ont retourné une valeur
    if dist_nominatim is not None and dist_ors is not None:
        if dist_nominatim == 0 and dist_ors == 0:
            final_distance = 0.0
            source = "both"
            status = "ok"
            message = "Même adresse confirmée par les deux services"
        elif dist_nominatim == 0 or dist_ors == 0:
            final_distance = max(dist_nominatim, dist_ors)
            source = "nominatim" if dist_nominatim > 0 else "ors"
            status = "ok"
            message = f"Distance nulle sur un service, prise de {source}"
        else:
            diff_percent = abs(dist_nominatim - dist_ors) / max(dist_nominatim, dist_ors) * 100
            if not quiet:
                logger.info(f"📐 Différence: {diff_percent:.2f}%")

            if diff_percent < DIFF_THRESHOLD_PERCENT:
                final_distance = round((dist_nominatim + dist_ors) / 2, 2)
                source = "average"
                status = "ok"
                message = f"Différence < {DIFF_THRESHOLD_PERCENT}%, moyenne prise"
            else:
                final_distance = min(dist_nominatim, dist_ors)
                source = "nominatim" if dist_nominatim < dist_ors else "ors"
                status = "warning"
                message = f"Différence importante ({diff_percent:.1f}%), prise de la plus petite valeur ({source})"

    # Seulement Nominatim
    elif dist_nominatim is not None:
        final_distance = dist_nominatim
        source = "nominatim"
        status = "ok"
        message = "Seul Nominatim a fourni une distance"

    # Seulement ORS
    elif dist_ors is not None:
        final_distance = dist_ors
        source = "ors"
        status = "ok"
        message = "Seul ORS a fourni une distance"

    # Aucun service
    else:
        final_distance = None
        source = "none"
        status = "error"
        message = "Aucune distance calculable (erreur de géolocalisation)"

    if not quiet:
        logger.info(f"🎯 DÉCISION FINALE: {final_distance} km (source: {source}, status: {status})")
        logger.info(f"💬 Message: {message}")
        logger.info(f"{'='*80}\n")

    return BatchDistanceResult(
        final_distance=final_distance,
        nominatim_distance=dist_nominatim,
        ors_distance=dist_ors,
        source=source,
        status=status,
        message=message,
        address1=address1,
        address2=address2
    )


def _calculate_with_nominatim_cached(address1: str,
                                      address2: str,
                                      region1: Optional[str] = None,
                                      region2: Optional[str] = None,
                                      quiet: bool = False) -> Optional[float]:
    """Calcule la distance avec Nominatim (version avec cache)"""
    try:
        coords1 = get_coordinates_nominatim_cached(address1, region1)
        coords2 = get_coordinates_nominatim_cached(address2, region2)

        if coords1 is None or coords2 is None:
            return None

        distance = geodesic(coords1, coords2).kilometers

        if distance < 1.0:
            return 0.0

        distance_routiere = distance * ROAD_FACTOR
        return round(distance_routiere, 2)

    except Exception as e:
        if not quiet:
            logger.error(f"Erreur calcul Nominatim pour {address1} -> {address2}: {str(e)}")
        return None


def _calculate_with_ors_cached(address1: str,
                                address2: str,
                                api_key: str,
                                region1: Optional[str] = None,
                                region2: Optional[str] = None,
                                quiet: bool = False) -> Optional[float]:
    """Calcule la distance avec ORS (version avec cache)"""
    try:
        coords1 = get_coordinates_ors_cached(address1, api_key, region1)
        coords2 = get_coordinates_ors_cached(address2, api_key, region2)

        if coords1 is None or coords2 is None:
            return None

        distance = geodesic(coords1, coords2).kilometers

        if distance < 1.0:
            return 0.0

        distance_routiere = distance * ROAD_FACTOR
        return round(distance_routiere, 2)

    except Exception as e:
        if not quiet:
            logger.error(f"Erreur calcul ORS pour {address1} -> {address2}: {str(e)}")
        return None


def calculate_batch_distances_parallel(addresses_pairs: List[tuple],
                                        api_key_ors: Optional[str] = None,
                                        max_workers: int = MAX_WORKERS,
                                        quiet: bool = True) -> List[BatchDistanceResult]:
    """
    Calcule plusieurs distances en parallèle

    Args:
        addresses_pairs: Liste de tuples (address1, address2)
        api_key_ors: Clé API OpenRouteService
        max_workers: Nombre de threads parallèles
        quiet: Mode silencieux

    Returns:
        Liste de BatchDistanceResult dans le même ordre
    """
    results = [None] * len(addresses_pairs)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre tous les calculs
        future_to_index = {
            executor.submit(
                calculate_batch_distance,
                addr1, addr2,
                api_key_ors=api_key_ors,
                quiet=quiet
            ): idx
            for idx, (addr1, addr2) in enumerate(addresses_pairs)
        }

        # Collecter les résultats
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(f"Erreur lors du calcul de la distance {idx}: {str(e)}")
                # Créer un résultat d'erreur
                addr1, addr2 = addresses_pairs[idx]
                results[idx] = BatchDistanceResult(
                    final_distance=None,
                    nominatim_distance=None,
                    ors_distance=None,
                    source="none",
                    status="error",
                    message=f"Erreur: {str(e)}",
                    address1=addr1,
                    address2=addr2
                )

    return results
