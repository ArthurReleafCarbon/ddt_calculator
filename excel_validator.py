"""
Module de validation du fichier Excel d'entrée pour le calculateur de distance domicile-travail.
Ce module vérifie la structure et l'intégrité des données avant le traitement.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Résultat de la validation d'un fichier Excel"""
    is_valid: bool
    total_rows: int
    valid_rows: int
    errors: List[str]
    warnings: List[str]
    column_info: Dict[str, any]


class ExcelValidator:
    """Validateur pour les fichiers Excel de données domicile-travail"""

    # Configuration de la structure attendue
    SHEET_NAME = "Questionnaire dom-travail"
    SKIP_ROWS = 5

    # Index des colonnes importantes (après skiprows)
    COL_RESIDENCE = 5      # Colonne F: Commune de résidence
    COL_JOURS_SITE = 6     # Colonne G: Jours par semaine
    COL_TRANSPORT = 7      # Colonne H: Mode de transport
    COL_VEHICLE = 8        # Colonne I: Type de véhicule
    COL_ENERGY = 9         # Colonne J: Type d'énergie
    COL_TRAVAIL = 11       # Colonne L: Lieu de travail

    # Colonnes obligatoires (doivent avoir au moins une valeur non-NaN)
    REQUIRED_COLUMNS = {
        COL_RESIDENCE: "Commune de résidence (Colonne F)",
        COL_JOURS_SITE: "Nombre de jours travaillés sur site (Colonne G)",
        COL_TRANSPORT: "Moyen de transport principal (Colonne H)",
        COL_TRAVAIL: "Lieu de travail (Colonne L)"
    }

    # Colonnes conditionnellement obligatoires (obligatoires seulement si transport = voiture)
    CONDITIONAL_COLUMNS = {
        COL_VEHICLE: "Catégorie de voiture (Colonne I)",
        COL_ENERGY: "Énergie de voiture (Colonne J)"
    }

    MIN_COLUMNS_REQUIRED = 12  # Minimum de colonnes attendues

    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.result: Optional[ValidationResult] = None

    def validate_file(self, file_path_or_buffer) -> ValidationResult:
        """
        Valide un fichier Excel complet

        Args:
            file_path_or_buffer: Chemin vers le fichier ou buffer (uploaded file)

        Returns:
            ValidationResult: Résultat détaillé de la validation
        """
        errors = []
        warnings = []
        column_info = {}

        # Test 1: Lecture du fichier
        try:
            self.df = pd.read_excel(
                file_path_or_buffer,
                sheet_name=self.SHEET_NAME,
                skiprows=self.SKIP_ROWS
            )
        except ValueError as e:
            errors.append(f"❌ Feuille '{self.SHEET_NAME}' introuvable dans le fichier")
            return ValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings,
                column_info=column_info
            )
        except Exception as e:
            errors.append(f"❌ Erreur lors de la lecture du fichier: {str(e)}")
            return ValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings,
                column_info=column_info
            )

        # Test 2: Vérifier le nombre de colonnes
        num_columns = len(self.df.columns)
        column_info['num_columns'] = num_columns

        if num_columns < self.MIN_COLUMNS_REQUIRED:
            errors.append(
                f"❌ Nombre de colonnes insuffisant: {num_columns} trouvées, "
                f"{self.MIN_COLUMNS_REQUIRED} attendues minimum"
            )

        # Test 3: Vérifier que le DataFrame n'est pas vide
        total_rows = len(self.df)
        column_info['total_rows'] = total_rows

        if total_rows == 0:
            errors.append("❌ Le fichier ne contient aucune ligne de données")
            return ValidationResult(
                is_valid=False,
                total_rows=0,
                valid_rows=0,
                errors=errors,
                warnings=warnings,
                column_info=column_info
            )

        # Test 4: Valider les colonnes obligatoires
        for col_idx, col_name in self.REQUIRED_COLUMNS.items():
            if col_idx >= num_columns:
                errors.append(f"❌ {col_name} manquante (colonne inexistante)")
                continue

            col_data = self.df.iloc[:, col_idx]
            non_null_count = col_data.notna().sum()
            null_count = col_data.isna().sum()

            column_info[col_name] = {
                'non_null': int(non_null_count),
                'null': int(null_count),
                'percentage_filled': round((non_null_count / total_rows) * 100, 2)
            }

            if non_null_count == 0:
                errors.append(f"❌ {col_name} : AUCUNE donnée présente")
            elif null_count > 0:
                warnings.append(
                    f"⚠️ {col_name} : {null_count} cellule(s) vide(s) sur {total_rows} "
                    f"({round((null_count / total_rows) * 100, 2)}%)"
                )

        # Test 5: Analyser les colonnes conditionnelles (obligatoires si transport = voiture)
        for col_idx, col_name in self.CONDITIONAL_COLUMNS.items():
            if col_idx >= num_columns:
                warnings.append(f"⚠️ {col_name} manquante (colonne inexistante)")
                continue

            col_data = self.df.iloc[:, col_idx]
            non_null_count = col_data.notna().sum()
            null_count = col_data.isna().sum()

            column_info[col_name] = {
                'non_null': int(non_null_count),
                'null': int(null_count),
                'percentage_filled': round((non_null_count / total_rows) * 100, 2)
            }

            # Compter combien de lignes ont "voiture" comme transport
            if self.COL_TRANSPORT < num_columns:
                transport_col = self.df.iloc[:, self.COL_TRANSPORT]
                voiture_count = transport_col[transport_col.notna()].astype(str).str.lower().str.contains('voiture').sum()

                if voiture_count > 0 and null_count > 0:
                    warnings.append(
                        f"⚠️ {col_name} : {null_count} cellule(s) vide(s) "
                        f"(obligatoire pour les {voiture_count} ligne(s) avec transport = voiture)"
                    )

        # Test 6: Valider les données par ligne
        valid_rows = self._validate_rows()
        column_info['valid_rows'] = valid_rows
        column_info['invalid_rows'] = total_rows - valid_rows

        if valid_rows < total_rows:
            warnings.append(
                f"⚠️ {total_rows - valid_rows} ligne(s) ne contiennent pas toutes "
                f"les données obligatoires (résidence, jours/semaine, transport, travail + "
                f"véhicule et énergie si transport = voiture)"
            )

        # Test 7: Vérifier les valeurs de jours par semaine
        if self.COL_JOURS_SITE < num_columns:
            jours_col = self.df.iloc[:, self.COL_JOURS_SITE]
            jours_invalides = jours_col[(jours_col.notna()) &
                                        ((jours_col < 0) | (jours_col > 7))]

            if len(jours_invalides) > 0:
                warnings.append(
                    f"⚠️ {len(jours_invalides)} ligne(s) avec un nombre de jours/semaine "
                    f"invalide (doit être entre 0 et 7)"
                )

        # Déterminer si la validation est réussie
        is_valid = len(errors) == 0 and valid_rows > 0

        self.result = ValidationResult(
            is_valid=is_valid,
            total_rows=total_rows,
            valid_rows=valid_rows,
            errors=errors,
            warnings=warnings,
            column_info=column_info
        )

        return self.result

    def _validate_rows(self) -> int:
        """
        Compte le nombre de lignes valides (avec toutes les données obligatoires)

        Les colonnes véhicule et énergie ne sont obligatoires que si transport = voiture

        Returns:
            int: Nombre de lignes valides
        """
        if self.df is None or len(self.df.columns) < self.MIN_COLUMNS_REQUIRED:
            return 0

        valid_count = 0

        for idx, row in self.df.iterrows():
            # Vérifier que les colonnes obligatoires de base sont remplies
            residence = row.iloc[self.COL_RESIDENCE] if self.COL_RESIDENCE < len(row) else None
            jours = row.iloc[self.COL_JOURS_SITE] if self.COL_JOURS_SITE < len(row) else None
            transport = row.iloc[self.COL_TRANSPORT] if self.COL_TRANSPORT < len(row) else None
            travail = row.iloc[self.COL_TRAVAIL] if self.COL_TRAVAIL < len(row) else None

            # Vérifier les colonnes conditionnelles
            vehicle = row.iloc[self.COL_VEHICLE] if self.COL_VEHICLE < len(row) else None
            energy = row.iloc[self.COL_ENERGY] if self.COL_ENERGY < len(row) else None

            # Vérifier d'abord les colonnes obligatoires de base
            if not (pd.notna(residence) and pd.notna(jours) and pd.notna(transport) and pd.notna(travail)):
                continue

            # Vérifier que ce ne sont pas des chaînes vides
            residence_str = str(residence).strip()
            transport_str = str(transport).strip()
            travail_str = str(travail).strip()

            # Vérifier que les valeurs textuelles de base sont valides
            if not (residence_str and transport_str and travail_str and
                    residence_str.lower() != 'nan' and transport_str.lower() != 'nan' and
                    travail_str.lower() != 'nan'):
                continue

            # Vérifier que le nombre de jours est valide
            try:
                jours_float = float(jours)
                if not (0 <= jours_float <= 7):
                    continue
            except (ValueError, TypeError):
                continue

            # Vérifier les colonnes conditionnelles : véhicule et énergie obligatoires si transport = voiture
            is_voiture = 'voiture' in transport_str.lower()

            if is_voiture:
                # Si transport = voiture, véhicule et énergie sont obligatoires
                if not (pd.notna(vehicle) and pd.notna(energy)):
                    continue

                vehicle_str = str(vehicle).strip()
                energy_str = str(energy).strip()

                if not (vehicle_str and energy_str and
                        vehicle_str.lower() != 'nan' and energy_str.lower() != 'nan'):
                    continue

            # Si on arrive ici, la ligne est valide
            valid_count += 1

        return valid_count

    def get_columns_mapping(self) -> Dict[str, int]:
        """
        Retourne le mapping des colonnes utilisées

        Returns:
            Dict: Mapping nom -> index de colonne
        """
        return {
            'residence': self.COL_RESIDENCE,
            'jours_site': self.COL_JOURS_SITE,
            'transport': self.COL_TRANSPORT,
            'vehicle': self.COL_VEHICLE,
            'energy': self.COL_ENERGY,
            'travail': self.COL_TRAVAIL
        }

    def print_validation_report(self) -> None:
        """Affiche un rapport de validation formaté dans la console"""
        if self.result is None:
            print("❌ Aucune validation effectuée")
            return

        print("\n" + "="*70)
        print("📋 RAPPORT DE VALIDATION DU FICHIER EXCEL")
        print("="*70)

        print(f"\n📊 Statistiques générales:")
        print(f"  • Nombre total de lignes: {self.result.total_rows}")
        print(f"  • Lignes valides (données complètes): {self.result.valid_rows}")
        print(f"  • Lignes invalides: {self.result.total_rows - self.result.valid_rows}")
        print(f"  • Nombre de colonnes: {self.result.column_info.get('num_columns', 'N/A')}")

        if self.result.errors:
            print(f"\n🚫 Erreurs critiques ({len(self.result.errors)}):")
            for error in self.result.errors:
                print(f"  {error}")

        if self.result.warnings:
            print(f"\n⚠️  Avertissements ({len(self.result.warnings)}):")
            for warning in self.result.warnings:
                print(f"  {warning}")

        print(f"\n📈 Détail par colonne:")
        for col_name, col_stats in self.result.column_info.items():
            if isinstance(col_stats, dict):
                print(f"  • {col_name}:")
                print(f"    - Remplies: {col_stats['non_null']} ({col_stats['percentage_filled']}%)")
                print(f"    - Vides: {col_stats['null']}")

        print("\n" + "="*70)
        if self.result.is_valid:
            print("✅ VALIDATION RÉUSSIE - Le fichier peut être traité")
        else:
            print("❌ VALIDATION ÉCHOUÉE - Corrigez les erreurs avant de continuer")
        print("="*70 + "\n")


def validate_excel_file(file_path_or_buffer) -> ValidationResult:
    """
    Fonction helper pour valider rapidement un fichier Excel

    Args:
        file_path_or_buffer: Chemin vers le fichier ou buffer

    Returns:
        ValidationResult: Résultat de la validation
    """
    validator = ExcelValidator()
    result = validator.validate_file(file_path_or_buffer)
    validator.print_validation_report()
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python excel_validator.py <chemin_vers_fichier.xlsx>")
        sys.exit(1)

    file_path = sys.argv[1]
    print(f"🔍 Validation du fichier: {file_path}\n")

    result = validate_excel_file(file_path)

    sys.exit(0 if result.is_valid else 1)
