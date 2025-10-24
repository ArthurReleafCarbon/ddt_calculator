"""
Module de validation de fichiers Excel
(Renommé 'validation' au lieu de 'validators' pour éviter conflit avec le package pip validators)
"""

from .excel_validator import ExcelValidator

__all__ = ['ExcelValidator']
