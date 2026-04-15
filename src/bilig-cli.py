import re
import sys
from pathlib import Path

import click

from services.transaction_enhancer import TransactionEnhancer

sys.path.insert(0, str(Path(__file__).parent))

from services.csv_bank_data_reader import CsvBankDataReader
from services.file_reader import FileReader
from services.file_recorder import FileRecorder


@click.group()
def cli():
    pass


@cli.command()
@click.argument("input_path", default="data/boursobank", type=click.Path(exists=True))
@click.option("--parquet", is_flag=True, help="Also output a parquet file for pandas")
def extract(input_path: str, parquet: bool):
    """Extract and summarize transactions from CSV files found in INPUT_PATH."""
    paths = FileReader(input_path).get_csv_files()
    transactions = CsvBankDataReader().read(paths)

    accounts = sorted({t.account.account_label for t in transactions})
    dates = [t.dateOperation for t in transactions]
    oldest = min(dates).date()
    most_recent = max(dates).date()

    enhanced_transactions = TransactionEnhancer(transactions).get_enhanced_list()

    recorder = FileRecorder()
    csv_path = recorder.write_csv(enhanced_transactions)
    
    accounts_str = ", ".join(accounts[:-1]) + f" and {accounts[-1]}" if len(accounts) > 1 else accounts[0]
    click.echo(
        f"Found {len(transactions)} transactions, coming from {accounts_str} "
        f"between {oldest} and {most_recent}."
    )
    click.echo(f"Output written to {csv_path}.")

    if parquet:
        parquet_path = recorder.write_parquet(enhanced_transactions)
        click.echo(f"Parquet written to {parquet_path}.")


if __name__ == "__main__":
    cli()
