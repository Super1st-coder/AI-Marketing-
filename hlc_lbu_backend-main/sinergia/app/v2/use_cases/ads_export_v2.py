import pandas as pd
import logging
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import PatternFill, Font, Alignment

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ExcelManagerUseCaseV2:
    def __init__(self):
        logger.info("Initializing ExcelManagerUseCaseV2")

    def export_to_excel(self, data, filename="ads_export.xlsx"):
        df = self._transform_to_dataframe(data)

        if df.empty:
            logger.warning("No data to export. DataFrame is empty.")
            return None, filename, 400

        df["comments"] = ""

        cols = [c for c in df.columns if c not in ("status", "comments")]
        cols += ["status", "comments"]
        df = df[cols]

        temp_buffer = BytesIO()
        with pd.ExcelWriter(temp_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Ads_Data", index=False)

        temp_buffer.seek(0)
        wb = load_workbook(temp_buffer)
        ws = wb["Ads_Data"]

        header_fill = PatternFill(start_color="FF8811", end_color="FF8811", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment

        fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        fill_orange_light = PatternFill(start_color="FFF7EF", end_color="FFF7EF", fill_type="solid")

        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
            fill = fill_orange_light if (row[0].row % 2) == 0 else fill_white
            for cell in row:
                cell.fill = fill

        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        eval_col_index = None
        for idx, cell in enumerate(ws[1], start=1):
            if cell.value == "status":
                eval_col_index = idx
                break

        if eval_col_index:
            col_letter = ws.cell(row=1, column=eval_col_index).column_letter
            first_row, last_row = 2, ws.max_row

            if "Dropdowns" not in wb.sheetnames:
                ws_dropdown = wb.create_sheet("Dropdowns")
                ws_dropdown["A1"] = "aprobado"
                ws_dropdown["A2"] = "rechazado"
                ws_dropdown["A3"] = "pendiente"
                ws_dropdown.sheet_state = "hidden"

            dv = DataValidation(
                type="list",
                formula1="=Dropdowns!$A$1:$A$3",
                allow_blank=True
            )
            dv.add(f"{col_letter}{first_row}:{col_letter}{last_row}")
            ws.add_data_validation(dv)

        columns_to_hide = ["adset_id", "ad_id", "channel_id", "ad_channel_id"]
        for cell in ws[1]:
            if cell.value in columns_to_hide:
                col_letter = cell.column_letter
                ws.column_dimensions[col_letter].hidden = True

        final_buffer = BytesIO()
        wb.save(final_buffer)
        final_buffer.seek(0)

        logger.info(f"Excel file generated successfully: {filename}")
        return final_buffer.getvalue(), filename, 200

    def _transform_to_dataframe(self, ads_data):
        flattened_data = []
        if not ads_data:
            return pd.DataFrame()

        campaigns = ads_data.get("data", [])
        for campaign in campaigns:
            brand_name = campaign.get("brand_name")
            campaign_name = campaign.get("preferred_campaign", {}).get("title")

            for adset in campaign.get("adsets", []):
                adset_id = adset.get("id")
                adset_name = adset.get("name")

                for ad in adset.get("ads", []):
                    ad_id = ad.get("id")
                    ad_name = ad.get("name")

                    attributes_map = {attr["id"]: attr for attr in ad.get("channel_attributes", [])}

                    for channel in ad.get("channel_media_formats", []):
                        ad_channel_id = channel.get("ad_channel_id")
                        channel_id = channel.get("id")
                        channel_name = channel.get("name")
                        media_formats = channel.get("media_formats", [])

                        channel_attrs = attributes_map.get(channel_id, {})

                        attributes_values = {}
                        for field in ["primary_text", "headline", "description", "cta"]:
                            values = channel_attrs.get(field, [])
                            if isinstance(values, list):
                                attributes_values[field] = [
                                    v.get("payload") for v in values if isinstance(v, dict) and v.get("payload")
                                ][:5]
                            elif isinstance(values, str):
                                attributes_values[field] = [values] if values else []
                            else:
                                attributes_values[field] = []

                        if media_formats:
                            for mf in media_formats:

                                row = {
                                    "brand_name": brand_name,
                                    "campaign_name": campaign_name,
                                    "adset_id": adset_id,
                                    "adset_name": adset_name,
                                    "ad_id": ad_id,
                                    "ad_name": ad_name,
                                    "ad_channel_id": ad_channel_id,
                                    "channel_id": channel_id,
                                    "channel_name": channel_name,
                                    "media_format_id": mf.get("id"),
                                    "dimensions": mf.get("dimensions"),
                                    "visual_url_editor": mf.get("visual_url_editor"),
                                    "new_visual_id": mf.get("new_visual_id"),
                                    "status": mf.get("status") if mf.get("status") not in (None, "") else "pendiente"
                                }

                                for field, values in attributes_values.items():
                                    if field == "cta":
                                        row["cta"] = values[0] if values else ""
                                    else:
                                        for i in range(1, 6):
                                            row[f"{field}_{i}"] = values[i - 1] if i <= len(values) else ""

                                flattened_data.append(row)
                        else:
                            row = {
                                "brand_name": brand_name,
                                "campaign_name": campaign_name,
                                "adset_id": adset_id,
                                "adset_name": adset_name,
                                "ad_id": ad_id,
                                "ad_name": ad_name,
                                "ad_channel_id": ad_channel_id,
                                "channel_id": channel_id,
                                "channel_name": channel_name,
                                "media_format_id": None,
                                "dimensions": None,
                                "visual_url_editor": None,
                                "new_visual_id": None,
                                "status": "pendiente"
                            }

                            for field, values in attributes_values.items():
                                if field == "cta":
                                        row["cta"] = values[0] if values else ""
                                else:
                                    for i in range(1, 6):
                                        row[f"{field}_{i}"] = values[i - 1] if i <= len(values) else ""

                            flattened_data.append(row)

                    if not ad.get("channel_media_formats"):
                        row = {
                            "brand_name": brand_name,
                            "campaign_name": campaign_name,
                            "adset_id": adset_id,
                            "adset_name": adset_name,
                            "ad_id": ad_id,
                            "ad_name": ad_name,
                            "ad_channel_id": None,
                            "channel_id": None,
                            "channel_name": None,
                            "media_format_id": None,
                            "dimensions": None,
                            "visual_url_editor": None,
                            "new_visual_id": None,
                            "status": "pendiente"
                        }

                        for field in ["primary_text", "headline", "description", "cta"]:
                            for i in range(1, 6):
                                row[f"{field}_{i}"] = ""
                        flattened_data.append(row)

        return pd.DataFrame(flattened_data)
