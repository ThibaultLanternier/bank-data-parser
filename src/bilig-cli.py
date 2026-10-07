import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent))

from logging_config import setup_logging
from services.csv_bank_data_reader import CsvBankDataReader
from services.file_reader import FileReader
from services.file_recorder import FileRecorder
from services.ofx_bank_data_reader import OfxBankDataReader
from services.qif_bank_data_reader import QifBankDataReader
from services.transaction_enhancer import TransactionEnhancer

_READERS = {
    "csv": (FileReader.get_csv_files, CsvBankDataReader),
    "ofx": (FileReader.get_ofx_files, OfxBankDataReader),
    "qif": (FileReader.get_qif_files, QifBankDataReader),
}


@click.group()
def cli():
    setup_logging()


@cli.command()
@click.argument("input_path", default="data/boursobank", type=click.Path(exists=True))
@click.option(
    "--file-type",
    type=click.Choice(list(_READERS), case_sensitive=False),
    default="ofx",
    show_default=True,
    help="Type of files to read from INPUT_PATH",
)
@click.option("--parquet", is_flag=True, help="Also output a parquet file for pandas")
def extract(input_path: str, file_type: str, parquet: bool):
    """Extract and summarize transactions from the CSV, OFX or QIF files found in INPUT_PATH."""
    get_files, reader_class = _READERS[file_type]
    paths = get_files(FileReader(input_path))
    transactions = reader_class().read(paths)
    click.echo(f"Read {len(transactions)} transactions from {len(paths)} {file_type.upper()} files.")
    if not transactions:
        raise click.ClickException(f"No transactions found in {file_type.upper()} files in {input_path}.")

    accounts = sorted({t.account.account_label for t in transactions})
    dates = [t.dateOperation for t in transactions]
    oldest = min(dates).date()
    most_recent = max(dates).date()

    click.echo("Starting transactions analysis and enhancement...")
    enhanced_transactions = TransactionEnhancer(transactions).get_enhanced_list()
    click.echo("Transactions analysis and enhancement completed.")

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
