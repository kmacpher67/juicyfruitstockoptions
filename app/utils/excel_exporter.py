import pandas as pd


def export_to_excel(df: pd.DataFrame, filename: str) -> str:
    """Export a DataFrame to an Excel file."""
    df.to_excel(filename, index=False)
    return filename
