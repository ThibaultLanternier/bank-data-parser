import calendar
import sys
from pathlib import Path

import click

sys.path.insert(0, str(Path(__file__).parent))

from entities.transaction import Transaction
from logging_config import setup_logging
from services.csv_bank_data_reader import CsvBankDataReader
from services.file_reader import FileReader
from services.file_recorder import FileRecorder
from services.ofx_bank_data_reader import OfxBankDataReader
from services.qif_bank_data_reader import QifBankDataReader
from services.transaction_enhancer import TransactionEnhancer
from services.transaction_grouper import TransactionGrouper

_READERS = {
    "csv": (FileReader.get_csv_files, CsvBankDataReader),
    "ofx": (FileReader.get_ofx_files, OfxBankDataReader),
    "qif": (FileReader.get_qif_files, QifBankDataReader),
}


def input_options(command):
    """Add the INPUT_PATH argument and the --file-type option shared by the commands reading transactions."""
    command = click.option(
        "--file-type",
        type=click.Choice(list(_READERS), case_sensitive=False),
        default="ofx",
        show_default=True,
        help="Type of files to read from INPUT_PATH",
    )(command)
    return click.argument("input_path", default="data/boursobank", type=click.Path(exists=True))(command)


def read_transactions(input_path: str, file_type: str) -> list[Transaction]:
    """Read the transactions of the files of the given type found in input_path, fail if there is none."""
    get_files, reader_class = _READERS[file_type]
    paths = get_files(FileReader(input_path))
    transactions = reader_class().read(paths)
    click.echo(f"Read {len(transactions)} transactions from {len(paths)} {file_type.upper()} files.")
    if not transactions:
        raise click.ClickException(f"No transactions found in {file_type.upper()} files in {input_path}.")
    return transactions


@click.group()
def cli():
    setup_logging()


@cli.command()
@input_options
@click.option("--parquet", is_flag=True, help="Also output a parquet file for pandas")
def extract(input_path: str, file_type: str, parquet: bool):
    """Extract and summarize transactions from the CSV, OFX or QIF files found in INPUT_PATH."""
    transactions = read_transactions(input_path, file_type)

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


def _format_amount(amount: float) -> str:
    """French format, like the CSV input: spaces as thousands separator, comma as decimal."""
    return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")


@cli.command()
@input_options
def report(input_path: str, file_type: str):
    """Report per month income, expenses, transactions and accounts of the CSV, OFX or QIF files in INPUT_PATH."""
    transactions = read_transactions(input_path, file_type)

    for year, summaries in TransactionGrouper(transactions).group_by_month().items():
        click.echo(f"\n{year}")
        for summary in summaries:
            click.echo(f"  {calendar.month_name[summary.month]}")
            click.echo(f"    Total Income : {_format_amount(summary.total_income)}")
            click.echo(f"    Total Expenses : {_format_amount(summary.total_expenses)}")
            click.echo(f"    Number of transactions : {summary.transaction_count}")
            click.echo(f"    Bank accounts : {', '.join(summary.account_numbers)}")


if __name__ == "__main__":
    cli()
