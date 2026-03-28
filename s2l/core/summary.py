"""Generate master summary sheets from ROI Excel files."""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def generate_summary_sheet(directory: str, save_path: str):
    """Generate a summary Excel sheet from all ROI Excel files in a directory."""
    directory_path = Path(directory)
    excel_files = list(directory_path.glob("*.xlsx")) + list(directory_path.glob("*.xls"))

    if not excel_files:
        logger.warning(f"No Excel files found in: {directory}")
        return

    results = []
    for file_path in excel_files:
        if "Summary" in file_path.name:
            continue
        try:
            logger.info(f"Processing: {file_path}")
            df = pd.read_excel(file_path)

            if df.empty or 'Label' not in df.columns or 'Integrated Density' not in df.columns:
                logger.warning(f"Skipping file with missing columns: {file_path}")
                continue

            last_label = df['Label'].dropna().iloc[-1] if not df['Label'].dropna().empty else 0
            results.append({
                'File Location': str(file_path),
                'Number of Objects': int(last_label),
                'Sum of Integrated Density': float(df['Integrated Density'].sum()),
            })
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    if not results:
        logger.warning("No valid Excel files were processed.")
        return

    results_df = pd.DataFrame(results)
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(save_path, engine='xlsxwriter') as writer:
        results_df.to_excel(writer, index=False, sheet_name='Summary')
        workbook = writer.book
        worksheet = writer.sheets['Summary']

        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        for col_num, value in enumerate(results_df.columns):
            worksheet.write(0, col_num, value, header_fmt)

        for i, col in enumerate(results_df.columns):
            max_len = max(results_df[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, max_len)

    logger.info(f"Summary generated: {save_path}")
