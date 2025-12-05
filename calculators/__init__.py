"""
Module de calcul de distances avec différents services de géolocalisation
"""

from .distance_calculator import calculate_distance, normalize_commune_name
from .dual_distance_calculator import calculate_distance_dual_validation
from .batch_distance_calculator import calculate_batch_distance, BatchDistanceResult
from .batch_distance_calculator_optimized import calculate_batch_distances_parallel
from .summary_calculator import create_summary_report, create_transport_mode_summary
from .geocoding_cache import get_cache, GeocodingCache
from .batch_processor import BatchProcessor

__all__ = [
    'calculate_distance',
    'normalize_commune_name',
    'calculate_distance_dual_validation',
    'calculate_batch_distance',
    'calculate_batch_distances_parallel',
    'BatchDistanceResult',
    'create_summary_report',
    'create_transport_mode_summary',
    'get_cache',
    'GeocodingCache',
    'BatchProcessor',
]
