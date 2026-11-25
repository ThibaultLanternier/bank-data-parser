from datetime import datetime, timedelta, timezone
from pathlib import Path

from services import file_recorder
from services.bank_balance import BankBalance

METRIC = "bank_account_balance_euros"


def _escape(value: str) -> str:
    # Label value escaping required by OpenMetrics
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _timestamp(day: datetime) -> int:
    # The end balance is the balance at 00:00 the next day, dates are taken as UTC
    next_day = day.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int(next_day.replace(tzinfo=timezone.utc).timestamp())


class BankBalanceToOpenMetrics:
    """Write the end of day balances of a BankBalance as an OpenMetrics file, to backfill Prometheus with promtool."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir

    def write_openmetrics(
        self,
        bank_balance: BankBalance,
        filename: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Path:
        if filename is None:
            filename = f"balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.om"
        output_path = (self.output_dir or file_recorder.OUTPUT_DIR) / filename

        lines = [
            f"# HELP {METRIC} Account balance at the end of the day",
            f"# TYPE {METRIC} gauge",
            f"# UNIT {METRIC} euros",
        ]
        for account, days in sorted(bank_balance.get_daily_series(date_from, date_to).items()):
            # One label per account for all samples, so that a label change does not split the series
            labels = f'account="{_escape(account)}",account_label="{_escape(bank_balance.get_account_label(account))}"'
            for day in days:
                # An unknown balance is missing data, not a zero
                if day.end_balance is not None:
                    lines.append(f"{METRIC}{{{labels}}} {day.end_balance:.2f} {_timestamp(day.start_date)}")
        lines.append("# EOF")

        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path
