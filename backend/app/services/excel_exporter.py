"""
Excel export service for analysis results.
"""
from typing import Dict, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import io
import logging

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
            
            # Define styles
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # Define status styles (matching UI)
            status_styles = {
                "ok": {"fill": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"), "font_color": "006100"},
                "prohibited": {"fill": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"), "font_color": "9C0006"},
                "foreign": {"fill": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"), "font_color": "9C6500"},
                "normative_violation": {"fill": PatternFill(start_color="FFCC99", end_color="FFCC99", fill_type="solid"), "font_color": "663300"},
            }
            
            # Border style
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
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
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # Write data rows (starting from row 2)
            current_row = 2
            for word_data in filtered_words:
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
                
                # Column 1: Page URL as hyperlink (if available)
                # Priority: word.page_url (for project exports) > global page_url > empty
                word_page_url = word_data.get("page_url")
                final_url = word_page_url or page_url
                if final_url:
                    url_cell = ws.cell(row=current_row, column=1, value=final_url)
                    url_cell.hyperlink = final_url
                    url_cell.style = "Hyperlink"
                    url_cell.border = thin_border
                    url_cell.alignment = Alignment(horizontal="left", vertical="center")
                else:
                    # Leave empty if no URL
                    ws.cell(row=current_row, column=1, value="").border = thin_border
                
                # Column 2: Word
                ws.cell(row=current_row, column=2, value=word).border = thin_border
                
                # Column 3: Count (right-aligned)
                count_cell = ws.cell(row=current_row, column=3, value=count)
                count_cell.border = thin_border
                count_cell.alignment = Alignment(horizontal="right")
                
                # Column 4: Status with styling
                status_cell = ws.cell(row=current_row, column=4, value=status)
                status_cell.border = thin_border
                status_cell.alignment = Alignment(horizontal="center")
                if status in status_styles:
                    status_cell.fill = status_styles[status]["fill"]
                    status_cell.font = Font(color=status_styles[status]["font_color"], bold=True)
                
                # Column 5: Category
                ws.cell(row=current_row, column=5, value=category_str).border = thin_border
                
                # Column 6: Recommendation/Article
                ws.cell(row=current_row, column=6, value=recommendation).border = thin_border
                
                current_row += 1
            
            # Auto-adjust column widths for readability
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
            
            # Freeze the header row (row 1)
            ws.freeze_panes = "A2"
            
            # Add auto-filter to the entire data range (header + all data rows)
            if current_row > 2:  # At least one data row
                last_row = current_row - 1
                ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{last_row}"
            else:
                # Only headers, no data
                ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"
            
            # Save to bytes
            excel_bytes = io.BytesIO()
            wb.save(excel_bytes)
            excel_bytes.seek(0)
            
            return excel_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating XLSX export: {e}")
            raise
