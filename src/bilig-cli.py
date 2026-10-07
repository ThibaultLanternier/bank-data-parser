import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent))

from logging_config import setup_logging
from services.csv_bank_data_reader import CsvBankDataReader
from services.file_reader import FileReader
from services.qif_bank_data_reader import QIFBankDataReader
from services.file_recorder import FileRecorder
from services.transaction_enhancer import TransactionEnhancer


@click.group()
def cli():
    setup_logging()


@cli.command()
@click.argument("input_path", default="data/boursobank", type=click.Path(exists=True))
@click.option("--parquet", is_flag=True, help="Also output a parquet file for pandas")
def extract(input_path: str, parquet: bool):
    """Extract and summarize transactions from CSV and QIF files found in INPUT_PATH."""
    file_reader = FileReader(input_path)
    csv_paths = file_reader.get_csv_files()
    qif_paths = file_reader.get_qif_files()
    paths = csv_paths + qif_paths
    if not paths:
        raise click.ClickException(f"No CSV or QIF file found in {input_path}.")

    transactions = CsvBankDataReader().read(csv_paths) + QIFBankDataReader().read(qif_paths)
    click.echo(f"Read {len(transactions)} transactions from {len(paths)} files.")

    accounts = sorted({t.account.account_label for t in transactions})
    dates = [t.dateOperation for t in transactions]
    oldest = min(dates).date()
    most_recent = max(dates).date()

    click.echo(f"Starting transactions analysis and enhancement...")
    enhanced_transactions = TransactionEnhancer(transactions).get_enhanced_list()
    click.echo(f"Transactions analysis and enhancement completed.")

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
