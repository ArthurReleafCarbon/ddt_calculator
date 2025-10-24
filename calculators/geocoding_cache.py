"""
Module de cache pour les géolocalisations
Évite de recalculer les coordonnées pour les mêmes adresses
"""
from typing import Optional, Tuple, Dict
import hashlib
import logging

logger = logging.getLogger(__name__)


class GeocodingCache:
    """Cache en mémoire pour les résultats de géolocalisation"""

    def __init__(self):
        self._cache: Dict[str, Optional[Tuple[float, float]]] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, address: str, service: str, region: Optional[str] = None) -> str:
        """Crée une clé unique pour le cache"""
        # Normaliser l'adresse pour le cache
        normalized = address.lower().strip()
        if region:
            normalized = f"{normalized}|{region.lower()}"
        # Ajouter le service pour différencier Nominatim et ORS
        key = f"{service}:{normalized}"
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, address: str, service: str, region: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """Récupère des coordonnées depuis le cache"""
        key = self._make_key(address, service, region)
        if key in self._cache:
            self._hits += 1
            logger.debug(f"🎯 Cache HIT pour {address} ({service})")
            return self._cache[key]
        else:
            self._misses += 1
            return None

    def set(self, address: str, service: str, coords: Optional[Tuple[float, float]], region: Optional[str] = None):
        """Stocke des coordonnées dans le cache"""
        key = self._make_key(address, service, region)
        self._cache[key] = coords
        logger.debug(f"💾 Cache SET pour {address} ({service})")

    def get_stats(self) -> dict:
        """Retourne les statistiques du cache"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            'hits': self._hits,
            'misses': self._misses,
            'total': total,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache)
        }

    def clear(self):
        """Vide le cache"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("🧹 Cache vidé")


# Instance globale du cache
_global_cache = GeocodingCache()


def get_cache() -> GeocodingCache:
    """Retourne l'instance globale du cache"""
    return _global_cache
