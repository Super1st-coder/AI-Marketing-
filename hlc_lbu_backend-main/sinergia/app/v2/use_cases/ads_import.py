import pandas as pd
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

import pdb

class ExcelReaderValidator:
    def __init__(self, required_columns=None, validation_rules=None):
        """
        Clase para leer y validar Excels generados por ExcelManagerUseCase

        Args:
            required_columns (list): Columnas mínimas que deben existir.
            validation_rules (list): Lista de reglas de validación.
                Ejemplo:
                [
                    {"type": "required_field", "field": "name"},
                    {"type": "non_empty", "field": "status"},
                    {"type": "allowed_values", "field": "status", "values": ["Active", "Inactive"]}
                ]
        """
        self.required_columns = required_columns or []
        self.validation_rules = validation_rules or []

    def read_excel(self, excel_file: BytesIO) -> pd.DataFrame:
        """
        Leer Excel en DataFrame y validar estructura.

        Args:
            excel_file (BytesIO): Archivo Excel en memoria.

        Returns:
            pd.DataFrame: DataFrame con los datos leídos.
        """
        try:
            df = pd.read_excel(excel_file, engine="openpyxl")

            if df.empty:
                raise ValueError("El archivo Excel está vacío.")

            missing = [c for c in self.required_columns if c not in df.columns]
            if missing:
                raise ValueError(f"Faltan columnas requeridas: {missing}")

            logger.info(f"Excel leído correctamente con {df.shape[0]} filas y {df.shape[1]} columnas")
            return df

        except Exception as e:
            logger.error(f"Error leyendo Excel: {str(e)}", exc_info=True)
            raise

    def validate_dataframe(self, df: pd.DataFrame) -> dict:
        """
        Validar DataFrame según reglas.

        Args:
            df (pd.DataFrame): DataFrame a validar.

        Returns:
            dict: Resultados de la validación.
        """
        errors = []

        for rule in self.validation_rules:
            rule_type = rule.get("type")
            field = rule.get("field")

            if rule_type == "required_field":
                if field not in df.columns:
                    errors.append(f"Falta la columna obligatoria: {field}")

            elif rule_type == "non_empty":
                if df[field].isna().any() or (df[field].astype(str).str.strip() == "").any():
                    errors.append(f"La columna {field} tiene celdas vacías")

            elif rule_type == "allowed_values":
                invalid_values = df[~df[field].isin(rule["values"])]
                if not invalid_values.empty:
                    errors.append(
                        f"Valores no permitidos en columna {field}: {', '.join(invalid_values[field].unique())}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def get_values(self, df: pd.DataFrame, brand_id=None, campaign_id=None) -> list:
        df = df.where(pd.notna(df), None)
        result = []

        grouped = df.groupby("ad_channel_id")

        for ad_channel_id, group in grouped:
            group_records = group.to_dict(orient="records")

            base = {
                "ad_channel_id": ad_channel_id,
                "adset_id": group_records[0].get("adset_id"),
                "ad_id": group_records[0].get("ad_id"),
                "channel_id": group_records[0].get("channel_id"),
            }

            if brand_id is not None:
                base["brand_id"] = brand_id
            if campaign_id is not None:
                base["campaign_id"] = campaign_id

            base["media_formats"] = [
                {
                    "id": r.get("media_format_id"),
                    "visual_url_editor": r.get("visual_url_editor"),
                    "new_visual_id": r.get("new_visual_id"),
                    "status": r.get("status"),
                }
                for r in group_records
            ]

            result.append(base)

        return result

