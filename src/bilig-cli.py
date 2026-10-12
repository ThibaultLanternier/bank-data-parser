import calendar
import sys
from pathlib import Path

import click
import questionary

sys.path.insert(0, str(Path(__file__).parent))

from entities.group import Group
from entities.transaction import Transaction
from logging_config import setup_logging
from services.categorize_session import Action, CategorizeSession, ClusterReview, PatternPreview, Progress
from services.csv_bank_data_reader import CsvBankDataReader
from services.file_reader import FileReader
from services.file_recorder import FileRecorder
from services.groups_file import GroupsFile
from services.ofx_bank_data_reader import OfxBankDataReader
from services.qif_bank_data_reader import QifBankDataReader
from services.transaction_enhancer import TransactionEnhancer
from services.transaction_grouper import TransactionGrouper

_READERS = {
    "csv": (FileReader.get_csv_files, CsvBankDataReader),
    "ofx": (FileReader.get_ofx_files, OfxBankDataReader),
    "qif": (FileReader.get_qif_files, QifBankDataReader),
}

DEFAULT_GROUPS_PATH = "data/groups.yaml"


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


def groups_option(command):
    """Add the --groups option giving the YAML file of the user groups."""
    return click.option(
        "--groups",
        "groups_path",
        type=click.Path(dir_okay=False),
        default=DEFAULT_GROUPS_PATH,
        show_default=True,
        help="YAML file mapping each group to its label patterns",
    )(command)


def load_groups(groups_path: str) -> list[Group]:
    """Groups of the groups file, none when it does not exist, fail when it is invalid."""
    try:
        groups = GroupsFile(groups_path).load()
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"Loaded {len(groups)} groups from {groups_path}.")
    return groups


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
@groups_option
@click.option("--parquet", is_flag=True, help="Also output a parquet file for pandas")
def extract(input_path: str, file_type: str, groups_path: str, parquet: bool):
    """Extract and summarize transactions from the CSV, OFX or QIF files found in INPUT_PATH."""
    groups = load_groups(groups_path)
    transactions = read_transactions(input_path, file_type)

    accounts = sorted({t.account.account_label for t in transactions})
    dates = [t.dateOperation for t in transactions]
    oldest = min(dates).date()
    most_recent = max(dates).date()

    click.echo("Starting transactions analysis and enhancement...")
    enhanced_transactions = TransactionEnhancer(transactions, groups).get_enhanced_list()
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
    """Report per month income, expenses, transfers, transactions and accounts of the files in INPUT_PATH."""
    transactions = TransactionEnhancer(read_transactions(input_path, file_type)).mark_internal_transactions()

    for year, summaries in TransactionGrouper(transactions).group_by_month().items():
        click.echo(f"\n{year}")
        for summary in summaries:
            click.echo(f"  {calendar.month_name[summary.month]}")
            click.echo(f"    From {summary.first_date:%d-%m-%Y} until {summary.last_date:%d-%m-%Y}")
            click.echo(f"    Total Income : {_format_amount(summary.total_income)}")
            click.echo(f"    Total Expenses : {_format_amount(summary.total_expenses)}")
            click.echo(f"    Total Transfers : {_format_amount(summary.total_transfers)}")
            click.echo(f"    Number of transactions : {summary.transaction_count}")
            click.echo(f"    Bank accounts : {', '.join(summary.account_numbers)}")



class QuestionaryUi:
    """Terminal prompts of the categorize session, questionary returns None on Ctrl+C."""

    RECENT_TRANSACTIONS = 8

    def show_cluster(self, review: ClusterReview, progress: Progress) -> None:
        click.echo()
        click.echo(
            f"[{progress.reviewed + 1} / {progress.reviewed + progress.remaining}]  "
            f"{progress.grouped_share:.0%} of transactions grouped"
        )
        periodicity = f"   every ~{review.periodicity} days" if review.periodicity else ""
        click.secho(
            f"Cluster \"{review.label}\"   {len(review.cluster.transactions)} transactions   "
            f"{_format_amount(review.total_amount)}{periodicity}",
            bold=True,
        )
        if review.match.groups:
            click.secho(f"Conflict between {', '.join(g.name for g in review.match.groups)}", fg="yellow")
        for t in review.recent_transactions(self.RECENT_TRANSACTIONS):
            group = f"  [{t.group.name}]" if t.group else ""
            label = t.label.get_label()[:50]
            click.echo(f"  {t.dateOperation:%Y-%m-%d}  {label:<50}  {_format_amount(t.amount):>14}{group}")
        hidden = len(review.cluster.transactions) - self.RECENT_TRANSACTIONS
        if hidden > 0:
            click.echo(f"  ... {hidden} more")

    def ask_action(self, can_undo: bool) -> Action | None:
        choices = [
            questionary.Choice("Assign a group", Action.ASSIGN, shortcut_key="a"),
            questionary.Choice("Skip", Action.SKIP, shortcut_key="s"),
            questionary.Choice(
                "Undo last assignment", Action.UNDO, shortcut_key="u", disabled=None if can_undo else "nothing to undo"
            ),
            questionary.Choice("Quit", Action.QUIT, shortcut_key="q"),
        ]
        return questionary.select("Action", choices=choices, use_shortcuts=True).ask()

    def ask_pattern(self, default: str) -> str | None:
        return questionary.text("Pattern", default=default).ask()

    def show_preview(self, preview: PatternPreview) -> None:
        click.echo(f"  matches {preview.inside} transactions of this cluster, {preview.outside} outside")

    def ask_group(self, group_names: list[str]) -> str | None:
        if not group_names:
            return questionary.text("Group (new)").ask()
        return questionary.autocomplete("Group", choices=group_names).ask()

    def confirm_shadowed(self, shadowing: list[Group]) -> bool | None:
        names = ", ".join(g.name for g in shadowing)
        message = f"{names} listed before already match some of these transactions, save anyway?"
        return questionary.confirm(message, default=False).ask()

    def show_message(self, message: str) -> None:
        click.echo(message)


@cli.command()
@input_options
@groups_option
def categorize(input_path: str, file_type: str, groups_path: str):
    """Interactively assign groups to the clusters of transactions of INPUT_PATH, saved in the groups file."""
    load_groups(groups_path)
    transactions = read_transactions(input_path, file_type)
    enhancer = TransactionEnhancer(transactions)
    enhancer.get_enhanced_list()

    assignments = CategorizeSession(enhancer, GroupsFile(groups_path)).run(QuestionaryUi())

    click.echo(f"\n{len(assignments)} assignments saved to {groups_path}.")
    for a in assignments:
        click.echo(f"  {a.group_name}: {a.pattern}")


if __name__ == "__main__":
    cli()
