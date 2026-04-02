"""
Excel export service for analysis results.
"""
from typing import Dict, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import io
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class ExcelExporter:
    """Exports analysis results to Excel format."""
    
    @staticmethod
    def export_analysis(
        analysis_data: dict,
        selected_statuses: Optional[List[str]] = None,
        page_url: Optional[str] = None,
        language: str = "ru"
    ) -> bytes:
        """
        Export analysis results to XLSX format.
        
        Args:
            analysis_data: Analysis results data (same structure as fz168 response)
            selected_statuses: List of statuses to include. If None/empty, all statuses are included
            page_url: URL of the analyzed page (will be shown in first column of each row)
            language: Language code for headers (ru or en)
            
        Returns:
            Bytes containing the XLSX file
        """
        try:
            all_words = analysis_data.get("all_words", [])
            total_words = len(all_words)
            logger.info(f"ExcelExporter: Starting export with {total_words} words, language={language}")

            # Filter words by selected statuses if provided (empty array means no words)
            if selected_statuses is not None and len(selected_statuses) > 0:
                filtered_words = [w for w in all_words if w.get("status") in selected_statuses]
            else:
                filtered_words = all_words
            
            # Get page URL from analysis_data if not explicitly provided
            if not page_url:
                source_info = analysis_data.get("source_info", {})
                if source_info and source_info.get("url"):
                    page_url = source_info["url"]
            
            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Analysis Results"

            total_rows = len(filtered_words)
            # For large datasets, use minimal styling to speed up save
            use_styling = total_rows <= 10000

            if use_styling:
                # Define styles only for smaller datasets
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")

                status_styles = {
                    "ok": {"fill": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"), "font_color": "006100"},
                    "prohibited": {"fill": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"), "font_color": "9C0006"},
                    "foreign": {"fill": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"), "font_color": "9C6500"},
                    "normative_violation": {"fill": PatternFill(start_color="FFCC99", end_color="FFCC99", fill_type="solid"), "font_color": "663300"},
                }

                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
            else:
                logger.info(f"ExcelExporter: Using minimal styling for large dataset ({total_rows} rows)")
                # Use simple default styles for large datasets
                header_font = Font(bold=True)
                header_fill = None
                header_alignment = Alignment(horizontal="center")
                status_styles = {}
                thin_border = None
            
            # Localized headers based on language
            headers_map = {
                "ru": ["Ссылка на страницу", "Слово", "Кол-во", "Статус", "Категория", "Рекомендация / Статья"],
                "en": ["Page URL", "Word", "Count", "Status", "Category", "Recommendation / Article"]
            }
            headers = headers_map.get(language, headers_map["ru"])
            
            # Write headers (row 1)
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                if header_fill:
                    cell.fill = header_fill
                cell.alignment = header_alignment
                if thin_border:
                    cell.border = thin_border
            
            # Write data rows (starting from row 2)
            current_row = 2
            total_rows = len(filtered_words)
            log_interval = max(10000, total_rows // 20)  # Log every 10k rows or 5% of data
            use_styling = total_rows <= 10000

            for idx, word_data in enumerate(filtered_words):
                # Log progress periodically for large datasets
                if idx % log_interval == 0:
                    logger.info(f"Excel export: processing row {idx + 1} of {total_rows} ({((idx + 1) / total_rows * 100):.1f}%)")

                word = word_data.get("word", "")
                count = word_data.get("count", 1)
                status = word_data.get("status", "")
                categories = word_data.get("categories", [])
                category_str = ", ".join(categories) if categories else ""

                # Get recommendation or law article
                recommendation = ""
                if word_data.get("law_article"):
                    recommendation = f"Статья: {word_data['law_article']}"
                elif word_data.get("recommendation"):
                    recommendation = word_data["recommendation"]
                elif status == "ok":
                    recommendation = "Соответствует нормам" if language == "ru" else "Complies with standards"

                # Column 1: Page URL (as plain text for large datasets to avoid hyperlink overhead)
                word_page_url = word_data.get("page_url")
                final_url = word_page_url or page_url
                ws.cell(row=current_row, column=1, value=final_url or "")

                # Column 2: Word
                ws.cell(row=current_row, column=2, value=word)

                # Column 3: Count
                ws.cell(row=current_row, column=3, value=count)

                # Column 4: Status
                ws.cell(row=current_row, column=4, value=status)

                # Column 5: Category
                ws.cell(row=current_row, column=5, value=category_str)

                # Column 6: Recommendation/Article
                ws.cell(row=current_row, column=6, value=recommendation)

                # Apply styling only for smaller datasets
                if use_styling and thin_border:
                    for col in range(1, 7):
                        ws.cell(row=current_row, column=col).border = thin_border

                    if status in status_styles:
                        status_cell = ws.cell(row=current_row, column=4)
                        status_cell.fill = status_styles[status]["fill"]
                        status_cell.font = Font(color=status_styles[status]["font_color"], bold=True)

                current_row += 1
            
            logger.info(f"Excel export: completed writing {total_rows} rows")
            
            # Optimization: Skip auto-column width adjustment for large datasets (>10k rows)
            # This is the slowest operation in openpyxl for large files
            total_rows = current_row - 1
            if total_rows <= 10000:
                logger.info(f"ExcelExporter: Starting column width adjustment for {total_rows} rows")
                column_widths = {
                    1: 40,  # Page URL
                    2: 30,  # Word
                    3: 12,  # Count
                    4: 20,  # Status
                    5: 25,  # Category
                    6: 50   # Recommendation/Article
                }
                for col_idx, width in column_widths.items():
                    ws.column_dimensions[get_column_letter(col_idx)].width = width
                logger.info(f"ExcelExporter: Column widths set")
            else:
                logger.info(f"ExcelExporter: Skipping column width adjustment for large dataset ({total_rows} rows)")

            # Freeze the header row (row 1) - this is fast
            ws.freeze_panes = "A2"
            logger.info(f"ExcelExporter: Frozen panes")

            # Add auto-filter only for moderate sized datasets
            if total_rows <= 50000:
                if total_rows > 0:  # At least one data row
                    last_row = current_row - 1
                    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last_row}"
                else:
                    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
                logger.info(f"ExcelExporter: Set auto-filter")
            else:
                logger.info(f"ExcelExporter: Skipping auto-filter for large dataset ({total_rows} rows)")

            logger.info(f"ExcelExporter: About to save workbook to BytesIO buffer")
            # Save to a BytesIO buffer to avoid filesystem corruption
            buffer = io.BytesIO()
            wb.save(buffer)
            logger.info(f"ExcelExporter: Workbook saved to buffer, getting bytes")
            data = buffer.getvalue()
            logger.info(f"ExcelExporter: Got {len(data)} bytes from buffer")
            buffer.close()
            wb.close()
            logger.info(f"ExcelExporter: Returning data to caller")
            return data
            
        except Exception as e:
            logger.error(f"Error generating XLSX export: {e}")
            raise
