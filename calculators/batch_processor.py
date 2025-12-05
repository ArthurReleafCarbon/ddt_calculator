"""
Module de traitement par batch avec sauvegarde temporaire
Permet de traiter de gros volumes en plusieurs lots et de récupérer en cas de crash
"""

import pandas as pd
import logging
from typing import List, Tuple, Optional, Callable, Any
from pathlib import Path
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Gestionnaire de traitement par batch avec sauvegarde temporaire"""

    def __init__(self, batch_size: int = 50, temp_dir: str = ".cache/temp_batches"):
        """
        Initialise le processeur par batch

        Args:
            batch_size: Nombre de lignes à traiter par batch
            temp_dir: Répertoire pour les fichiers temporaires
        """
        self.batch_size = batch_size
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def process_batches(
        self,
        df: pd.DataFrame,
        process_function: Callable,
        address1_col: str,
        address2_col: str,
        session_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        max_workers: int = 5,
        **kwargs
    ) -> Tuple[pd.DataFrame, dict]:
        """
        Traite le DataFrame par batch avec sauvegarde temporaire

        Args:
            df: DataFrame à traiter
            process_function: Fonction de calcul (ex: calculate_batch_distance)
            address1_col: Nom de la colonne adresse 1
            address2_col: Nom de la colonne adresse 2
            session_id: ID unique de la session
            progress_callback: Fonction de callback pour la progression (current, total, status)
            max_workers: Nombre de workers pour le ThreadPool
            **kwargs: Arguments supplémentaires pour process_function

        Returns:
            Tuple (DataFrame avec résultats, statistiques)
        """
        # Préparer les paires d'adresses valides
        addresses_pairs = []
        valid_indices = []

        for idx, row in df.iterrows():
            address1 = str(row[address1_col]).strip()
            address2 = str(row[address2_col]).strip()

            # Vérifier que les adresses ne sont pas vides
            if not address1 or address1 == "nan" or not address2 or address2 == "nan":
                continue

            addresses_pairs.append((address1, address2))
            valid_indices.append(idx)

        total_valid = len(addresses_pairs)
        total_batches = (total_valid + self.batch_size - 1) // self.batch_size

        logger.info(f"📦 Traitement par batch: {total_valid} lignes en {total_batches} batch(s)")

        # Vérifier si des résultats temporaires existent déjà
        existing_results = self._load_existing_results(session_id)
        start_batch = len(existing_results)

        if start_batch > 0:
            logger.info(f"🔄 Récupération de {start_batch} batch(s) déjà traité(s)")

        all_results = existing_results.copy()
        completed_items = start_batch * self.batch_size

        # Traiter batch par batch
        for batch_idx in range(start_batch, total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_valid)
            batch_pairs = addresses_pairs[start_idx:end_idx]
            batch_indices = valid_indices[start_idx:end_idx]

            logger.info(f"📦 Traitement du batch {batch_idx + 1}/{total_batches} ({len(batch_pairs)} lignes)")

            if progress_callback:
                progress_callback(
                    completed_items,
                    total_valid,
                    f"Batch {batch_idx + 1}/{total_batches}"
                )

            # Traiter le batch en parallèle
            batch_results = self._process_single_batch(
                batch_pairs,
                process_function,
                max_workers,
                **kwargs
            )

            # Sauvegarder le batch
            self._save_batch_results(session_id, batch_idx, batch_results, batch_indices)
            all_results.extend(batch_results)

            completed_items = len(all_results)

            if progress_callback:
                progress_callback(
                    completed_items,
                    total_valid,
                    f"Batch {batch_idx + 1}/{total_batches} terminé"
                )

        # Nettoyer les fichiers temporaires
        self._cleanup_session(session_id)

        # Construire le DataFrame de résultats
        result_df = self._build_result_dataframe(df, all_results, valid_indices, address1_col, address2_col)

        # Calculer les statistiques
        stats = self._compute_statistics(result_df)

        return result_df, stats

    def _process_single_batch(
        self,
        batch_pairs: List[Tuple[str, str]],
        process_function: Callable,
        max_workers: int,
        **kwargs
    ) -> List[Any]:
        """Traite un seul batch en parallèle"""
        results = [None] * len(batch_pairs)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    process_function,
                    addr1, addr2,
                    **kwargs
                ): idx
                for idx, (addr1, addr2) in enumerate(batch_pairs)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Erreur traitement ligne {idx}: {e}")
                    # Créer un résultat d'erreur
                    addr1, addr2 = batch_pairs[idx]
                    from calculators import BatchDistanceResult
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

    def _save_batch_results(
        self,
        session_id: str,
        batch_idx: int,
        results: List[Any],
        indices: List[int]
    ):
        """Sauvegarde les résultats d'un batch"""
        batch_file = self.temp_dir / f"{session_id}_batch_{batch_idx}.json"

        batch_data = {
            'batch_idx': batch_idx,
            'indices': indices,
            'results': [
                {
                    'final_distance': r.final_distance,
                    'nominatim_distance': r.nominatim_distance,
                    'ors_distance': r.ors_distance,
                    'source': r.source,
                    'status': r.status,
                    'message': r.message,
                    'address1': r.address1,
                    'address2': r.address2
                }
                for r in results
            ]
        }

        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Batch {batch_idx} sauvegardé: {batch_file}")

    def _load_existing_results(self, session_id: str) -> List[Any]:
        """Charge les résultats de batches déjà traités"""
        from calculators import BatchDistanceResult

        results = []
        batch_idx = 0

        while True:
            batch_file = self.temp_dir / f"{session_id}_batch_{batch_idx}.json"
            if not batch_file.exists():
                break

            try:
                with open(batch_file, 'r', encoding='utf-8') as f:
                    batch_data = json.load(f)

                for r in batch_data['results']:
                    results.append(BatchDistanceResult(
                        final_distance=r['final_distance'],
                        nominatim_distance=r['nominatim_distance'],
                        ors_distance=r['ors_distance'],
                        source=r['source'],
                        status=r['status'],
                        message=r['message'],
                        address1=r['address1'],
                        address2=r['address2']
                    ))

                batch_idx += 1

            except Exception as e:
                logger.error(f"Erreur chargement batch {batch_idx}: {e}")
                break

        return results

    def _cleanup_session(self, session_id: str):
        """Nettoie les fichiers temporaires d'une session"""
        batch_files = list(self.temp_dir.glob(f"{session_id}_batch_*.json"))
        for batch_file in batch_files:
            try:
                batch_file.unlink()
                logger.debug(f"🧹 Fichier temporaire supprimé: {batch_file}")
            except Exception as e:
                logger.warning(f"Impossible de supprimer {batch_file}: {e}")

    def _build_result_dataframe(
        self,
        original_df: pd.DataFrame,
        results: List[Any],
        valid_indices: List[int],
        address1_col: str,
        address2_col: str
    ) -> pd.DataFrame:
        """Construit le DataFrame de résultats"""
        df = original_df.copy()

        # Récupérer le nom de la colonne distance (3ème colonne)
        col_names = df.columns.tolist()
        distance_col = col_names[2] if len(col_names) > 2 else "Distance (km)"

        # Initialiser les listes avec des valeurs par défaut
        distances = [None] * len(df)
        sources = ["none"] * len(df)
        statuses = ["error"] * len(df)
        messages = ["Adresse manquante"] * len(df)
        nominatim_distances = [None] * len(df)
        ors_distances = [None] * len(df)

        # Remplir avec les résultats valides
        for idx, result in zip(valid_indices, results):
            distances[idx] = result.final_distance
            sources[idx] = result.source
            statuses[idx] = result.status
            messages[idx] = result.message
            nominatim_distances[idx] = result.nominatim_distance
            ors_distances[idx] = result.ors_distance

        # Mise à jour du DataFrame
        df[distance_col] = distances
        df["Source"] = sources
        df["Statut"] = statuses
        df["Message"] = messages
        df["Distance Nominatim (km)"] = nominatim_distances
        df["Distance ORS (km)"] = ors_distances

        return df

    def _compute_statistics(self, df: pd.DataFrame) -> dict:
        """Calcule les statistiques sur les résultats"""
        statuses = df["Statut"].tolist()
        sources = df["Source"].tolist()

        success_count = sum(1 for s in statuses if s == "ok")
        warning_count = sum(1 for s in statuses if s == "warning")
        error_count = sum(1 for s in statuses if s == "error")

        average_count = sum(1 for src in sources if src == "average")
        nominatim_only_count = sum(1 for src in sources if src == "nominatim")
        ors_only_count = sum(1 for src in sources if src == "ors")

        return {
            'success_count': success_count,
            'warning_count': warning_count,
            'error_count': error_count,
            'average_count': average_count,
            'nominatim_only_count': nominatim_only_count,
            'ors_only_count': ors_only_count,
            'total': len(df)
        }

    def has_pending_session(self, session_id: str) -> Tuple[bool, int]:
        """
        Vérifie si une session a des résultats en attente

        Returns:
            Tuple (has_pending, num_batches)
        """
        batch_files = list(self.temp_dir.glob(f"{session_id}_batch_*.json"))
        return len(batch_files) > 0, len(batch_files)

    def get_partial_results(self, session_id: str, original_df: pd.DataFrame, address1_col: str, address2_col: str) -> Optional[pd.DataFrame]:
        """
        Récupère les résultats partiels d'une session crashée

        Args:
            session_id: ID de la session
            original_df: DataFrame original
            address1_col: Nom colonne adresse 1
            address2_col: Nom colonne adresse 2

        Returns:
            DataFrame avec les résultats partiels ou None
        """
        existing_results = self._load_existing_results(session_id)

        if not existing_results:
            return None

        # Préparer les indices valides
        valid_indices = []
        addresses_pairs = []

        for idx, row in original_df.iterrows():
            address1 = str(row[address1_col]).strip()
            address2 = str(row[address2_col]).strip()

            if not address1 or address1 == "nan" or not address2 or address2 == "nan":
                continue

            addresses_pairs.append((address1, address2))
            valid_indices.append(idx)

        # Ne prendre que les indices correspondant aux résultats existants
        valid_indices = valid_indices[:len(existing_results)]

        result_df = self._build_result_dataframe(
            original_df,
            existing_results,
            valid_indices,
            address1_col,
            address2_col
        )

        return result_df
