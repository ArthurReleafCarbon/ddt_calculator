"""
Module de cache pour les géolocalisations
Évite de recalculer les coordonnées pour les mêmes adresses
Cache persistant avec SQLite pour réutilisation entre sessions
"""
from typing import Optional, Tuple, Dict
import hashlib
import logging
import sqlite3
import os
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class GeocodingCache:
    """Cache persistant avec SQLite pour les résultats de géolocalisation"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialise le cache persistant

        Args:
            db_path: Chemin vers la base de données SQLite (par défaut: .cache/geocoding_cache.db)
        """
        if db_path is None:
            # Créer le dossier .cache à la racine du projet
            cache_dir = Path(".cache")
            cache_dir.mkdir(exist_ok=True)
            db_path = str(cache_dir / "geocoding_cache.db")

        self.db_path = db_path
        self._hits = 0
        self._misses = 0

        # Initialiser la base de données
        self._init_db()

    def _init_db(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Créer la table si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS geocoding_cache (
                key TEXT PRIMARY KEY,
                address TEXT NOT NULL,
                service TEXT NOT NULL,
                region TEXT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index pour améliorer les performances
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_address_service
            ON geocoding_cache(address, service)
        """)

        conn.commit()
        conn.close()
        logger.info(f"💾 Cache persistant initialisé: {self.db_path}")

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

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT latitude, longitude
                FROM geocoding_cache
                WHERE key = ?
            """, (key,))

            result = cursor.fetchone()
            conn.close()

            if result:
                self._hits += 1
                lat, lon = result
                # Gérer le cas où les coordonnées sont NULL (adresse non trouvée)
                if lat is None or lon is None:
                    logger.debug(f"🎯 Cache HIT (NULL) pour {address} ({service})")
                    return None
                logger.debug(f"🎯 Cache HIT pour {address} ({service})")
                return (lat, lon)
            else:
                self._misses += 1
                return None

        except Exception as e:
            logger.error(f"Erreur lecture cache: {e}")
            self._misses += 1
            return None

    def set(self, address: str, service: str, coords: Optional[Tuple[float, float]], region: Optional[str] = None):
        """Stocke des coordonnées dans le cache"""
        key = self._make_key(address, service, region)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Extraire lat/lon ou NULL si coords est None
            lat = coords[0] if coords else None
            lon = coords[1] if coords else None

            # INSERT OR REPLACE pour mettre à jour si existe déjà
            cursor.execute("""
                INSERT OR REPLACE INTO geocoding_cache
                (key, address, service, region, latitude, longitude, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, address, service, region, lat, lon))

            conn.commit()
            conn.close()
            logger.debug(f"💾 Cache SET pour {address} ({service})")

        except Exception as e:
            logger.error(f"Erreur écriture cache: {e}")

    def get_stats(self) -> dict:
        """Retourne les statistiques du cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Compter le nombre d'entrées dans la base
            cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
            cache_size = cursor.fetchone()[0]

            conn.close()

            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                'hits': self._hits,
                'misses': self._misses,
                'total': total,
                'hit_rate': hit_rate,
                'cache_size': cache_size
            }
        except Exception as e:
            logger.error(f"Erreur stats cache: {e}")
            return {
                'hits': self._hits,
                'misses': self._misses,
                'total': self._hits + self._misses,
                'hit_rate': 0,
                'cache_size': 0
            }

    def clear(self):
        """Vide le cache (supprime toutes les entrées)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM geocoding_cache")
            conn.commit()
            conn.close()
            self._hits = 0
            self._misses = 0
            logger.info("🧹 Cache vidé")
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")

    def get_cache_info(self) -> dict:
        """Retourne des informations détaillées sur le cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Nombre total d'entrées
            cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
            total_entries = cursor.fetchone()[0]

            # Répartition par service
            cursor.execute("""
                SELECT service, COUNT(*)
                FROM geocoding_cache
                GROUP BY service
            """)
            by_service = dict(cursor.fetchall())

            # Taille du fichier DB
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)

            conn.close()

            return {
                'total_entries': total_entries,
                'by_service': by_service,
                'db_size_mb': round(db_size_mb, 2),
                'db_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Erreur info cache: {e}")
            return {}


# Instance globale du cache
_global_cache = GeocodingCache()


def get_cache() -> GeocodingCache:
    """Retourne l'instance globale du cache"""
    return _global_cache
