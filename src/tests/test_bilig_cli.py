import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

import services.file_recorder
from entities.account import Account
from entities.category import Category
from entities.label import Label
from entities.transaction import Transaction
from entities.transaction_cluster import TransactionCluster
from services.categorize_session import ClusterReview, Progress
from services.group_matcher import ClusterMatch, ClusterStatus

_CLI_PATH = Path(__file__).parent.parent / "bilig-cli.py"
_spec = importlib.util.spec_from_file_location("bilig_cli", _CLI_PATH)
bilig_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bilig_cli)

OFX_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS>
<BANKACCTFROM><ACCTID>00040079727</ACCTID></BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN><DTPOSTED>20261002</DTPOSTED><TRNTYPE>DEBIT</TRNTYPE><TRNAMT>-92.72</TRNAMT><FITID>fit1</FITID><NAME>CARTE 01/10/26 LIDL 2652 CB*6863</NAME></STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""  # noqa: E501 raw OFX export sample

QIF_CONTENT = """!Type:Bank
D02/10/2026
T-92.72
PCARTE 01/10/26 LIDL 2652 CB*6863
^
D01/10/2026
T3,000.00
PVIR SEPA M. DUPONT
^
"""


@pytest.fixture
def input_dir(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(services.file_recorder, "OUTPUT_DIR", output)
    data = tmp_path / "data"
    data.mkdir()
    (data / "export.ofx").write_text(OFX_CONTENT, encoding="utf-8")
    (data / "export.qif").write_text(QIF_CONTENT, encoding="utf-8")
    return data


class TestExtractCommand:
    def test_reads_ofx_files_by_default(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir)])
        assert result.exit_code == 0, result.output
        assert "Read 1 transactions from 1 OFX files." in result.output

    def test_reads_only_selected_file_type(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--file-type", "QIF"])
        assert result.exit_code == 0, result.output
        assert "Read 2 transactions from 1 QIF files." in result.output

    def test_fails_when_no_file_of_selected_type(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--file-type", "csv"])
        assert result.exit_code != 0
        assert "No transactions found in CSV files" in result.output

    def test_rejects_unknown_file_type(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--file-type", "pdf"])
        assert result.exit_code == 2


class TestExtractGroups:
    def _rows(self, input_dir):
        output = services.file_recorder.OUTPUT_DIR
        [csv_path] = output.glob("*.csv")
        return csv_path.read_text(encoding="utf-8-sig").splitlines()

    def test_uses_given_groups_file(self, input_dir, tmp_path):
        groups = tmp_path / "groups.yaml"
        groups.write_text("FOOD:\n  - lidl\n", encoding="utf-8")

        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--groups", str(groups)])

        assert result.exit_code == 0, result.output
        assert "Loaded 1 groups" in result.output
        header, row = self._rows(input_dir)
        values = dict(zip(header.split(";"), row.split(";")))
        assert (values["group"], values["group_source"]) == ("FOOD", "direct")

    def test_missing_groups_file_means_no_group(self, input_dir, tmp_path):
        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--groups", str(tmp_path / "none.yaml")])

        assert result.exit_code == 0, result.output
        assert "Loaded 0 groups" in result.output

    def test_fails_on_invalid_groups_file(self, input_dir, tmp_path):
        groups = tmp_path / "groups.yaml"
        groups.write_text("FOOD: lidl\n", encoding="utf-8")

        result = CliRunner().invoke(bilig_cli.cli, ["extract", str(input_dir), "--groups", str(groups)])

        assert result.exit_code == 1
        assert "Invalid groups file" in result.output


class TestCategorizeCommand:
    def test_exits_when_no_cluster_is_left_to_review(self, input_dir, tmp_path):
        groups = tmp_path / "groups.yaml"
        groups.write_text("FOOD:\n  - lidl\n", encoding="utf-8")

        result = CliRunner().invoke(bilig_cli.cli, ["categorize", str(input_dir), "--groups", str(groups)])

        assert result.exit_code == 0, result.output
        assert "No cluster left to review." in result.output
        assert "0 assignments saved to" in result.output

    def test_fails_on_invalid_groups_file(self, input_dir, tmp_path):
        groups = tmp_path / "groups.yaml"
        groups.write_text("- lidl\n", encoding="utf-8")

        result = CliRunner().invoke(bilig_cli.cli, ["categorize", str(input_dir), "--groups", str(groups)])

        assert result.exit_code == 1
        assert "Invalid groups file" in result.output


class TestReportCommand:
    def test_reports_each_month_of_each_year(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["report", str(input_dir), "--file-type", "qif"])
        assert result.exit_code == 0, result.output
        assert "Read 2 transactions from 1 QIF files." in result.output
        assert result.output.endswith(
            "\n2026\n"
            "  October\n"
            "    From 01-10-2026 until 02-10-2026\n"
            "    Total Income : 3 000,00 €\n"
            "    Total Expenses : 92,72 €\n"
            "    Total Transfers : 0,00 €\n"
            "    Number of transactions : 2\n"
            "    Bank accounts : export\n"
        )

    def test_reads_ofx_files_by_default(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["report", str(input_dir)])
        assert result.exit_code == 0, result.output
        assert "Read 1 transactions from 1 OFX files." in result.output
        assert "Bank accounts : 00040079727" in result.output

    def test_fails_when_no_file_of_selected_type(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["report", str(input_dir), "--file-type", "csv"])
        assert result.exit_code != 0
        assert "No transactions found in CSV files" in result.output

    def test_excludes_transfers_between_accounts(self, input_dir):
        (input_dir / "savings.qif").write_text(
            "!Type:Bank\nD02/10/2026\nT92.72\nPVIR INTERNE\n^\n", encoding="utf-8"
        )
        result = CliRunner().invoke(bilig_cli.cli, ["report", str(input_dir), "--file-type", "qif"])
        assert result.exit_code == 0, result.output
        assert result.output.endswith(
            "    Total Income : 3 000,00 €\n"
            "    Total Expenses : 0,00 €\n"
            "    Total Transfers : 92,72 €\n"
            "    Number of transactions : 3\n"
            "    Bank accounts : export, savings\n"
        )


BALANCE_CSV = (
    "dateOp;dateVal;label;category;categoryParent;supplierFound;amount;comment;accountNum;accountLabel;accountbalance\n"
    "2022-12-30;2022-12-30;A | A;misc;misc;;-77,97;;00001;Main;10105.11\n"
    "2023-01-02;2023-01-02;B | B;misc;misc;;2950,00;;00001;Main;12190.60\n"
    "2023-01-02;2023-01-02;C | C;misc;misc;;-868,50;;00001;Main;12190.60\n"
)


class TestBalanceCommand:
    def test_reports_gaps_and_writes_csv(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(bilig_cli.cli, ["balance", str(input_dir)])

        assert result.exit_code == 0, result.output
        assert "Read 3 transactions from 1 CSV files." in result.output
        assert "Main (00001): 2 days from 2022-12-30 to 2023-01-02, 0 inferred, 0 without balance" in result.output
        assert "Gap: 00001 between 2022-12-30 and 2023-01-02, 3,99 € missing" in result.output
        assert "1 gaps, 0 conflicts." in result.output
        assert "Account: Main (00001) missing data between 2022-12-31 and 2023-01-01" in result.output
        [output_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.csv"))
        assert f"Output written to {output_file}." in result.output
        # Header + one row per calendar day from 2022-12-30 to 2023-01-02
        assert len(output_file.read_text(encoding="utf-8-sig").splitlines()) == 5

    def test_writes_the_given_range(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(
            bilig_cli.cli, ["balance", str(input_dir), "--from", "2022-12-31", "--to", "2023-01-05"]
        )

        assert result.exit_code == 0, result.output
        # The summary still counts the days with transactions of the whole history
        assert "Main (00001): 2 days from 2022-12-30 to 2023-01-02" in result.output
        [output_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.csv"))
        dates = [line.split(";")[2] for line in output_file.read_text(encoding="utf-8-sig").splitlines()[1:]]
        assert dates == ["2022-12-31", "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
        assert "Account: Main (00001) missing data between 2022-12-31 and 2023-01-01" in result.output
        assert "Account: Main (00001) missing data between 2023-01-03 and 2023-01-05" in result.output

    def test_writes_openmetrics_file_with_the_flag(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(bilig_cli.cli, ["balance", str(input_dir), "--openmetrics"])

        assert result.exit_code == 0, result.output
        [csv_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.csv"))
        [om_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.om"))
        assert f"Output written to {csv_file}." in result.output
        assert f"OpenMetrics output written to {om_file}." in result.output
        samples = [line for line in om_file.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
        # 2022-12-31 and 2023-01-01 are in a gap and have no sample
        assert samples == [
            'bank_account_balance_euros{account="00001",account_label="Main"} 10105.11 1672444800',
            'bank_account_balance_euros{account="00001",account_label="Main"} 12190.60 1672704000',
        ]

    def test_writes_openmetrics_file_for_the_given_range(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(
            bilig_cli.cli, ["balance", str(input_dir), "--openmetrics", "--from", "2023-01-01", "--to", "2023-01-05"]
        )

        assert result.exit_code == 0, result.output
        [om_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.om"))
        samples = [line for line in om_file.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
        assert [line.split(" ")[-1] for line in samples] == ["1672704000"]

    def test_writes_no_openmetrics_file_without_the_flag(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(bilig_cli.cli, ["balance", str(input_dir)])

        assert result.exit_code == 0, result.output
        assert not list(services.file_recorder.OUTPUT_DIR.glob("balance_*.om"))
        assert not list(services.file_recorder.OUTPUT_DIR.glob("balance_*.jsonl"))
        assert "OpenMetrics" not in result.output
        assert "Transactions output" not in result.output

    def test_writes_transactions_file_with_the_flag(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(bilig_cli.cli, ["balance", str(input_dir), "--openmetrics"])

        assert result.exit_code == 0, result.output
        [jsonl_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.jsonl"))
        assert f"Transactions output written to {jsonl_file}." in result.output
        records = [json.loads(line) for line in jsonl_file.read_text(encoding="utf-8").splitlines()]
        assert [(r["date_value"], r["amount"], r["label"]) for r in records] == [
            ("2022-12-30", -77.97, "a"),
            ("2023-01-02", 2950.0, "b"),
            ("2023-01-02", -868.5, "c"),
        ]

    def test_writes_transactions_file_for_the_given_range(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(
            bilig_cli.cli, ["balance", str(input_dir), "--openmetrics", "--from", "2023-01-01", "--to", "2023-01-05"]
        )

        assert result.exit_code == 0, result.output
        [jsonl_file] = list(services.file_recorder.OUTPUT_DIR.glob("balance_*.jsonl"))
        dates = [json.loads(line)["date_operation"] for line in jsonl_file.read_text(encoding="utf-8").splitlines()]
        assert dates == ["2023-01-02", "2023-01-02"]

    def test_fails_when_from_is_after_to(self, input_dir):
        (input_dir / "export.csv").write_text(BALANCE_CSV, encoding="utf-8-sig")

        result = CliRunner().invoke(
            bilig_cli.cli, ["balance", str(input_dir), "--from", "2026-04-01", "--to", "2026-03-01"]
        )

        assert result.exit_code != 0
        assert "the start date is after the end date" in result.output

    def test_fails_without_csv_files(self, input_dir):
        result = CliRunner().invoke(bilig_cli.cli, ["balance", str(input_dir)])

        assert result.exit_code != 0
        assert "No transactions found in CSV files" in result.output


class TestQuestionaryUi:
    @staticmethod
    def _transaction(amount: float, day: int, is_internal: bool) -> Transaction:
        date = datetime(2024, 1, day)
        t = Transaction(date, date, Label("VIR LIVRET A | VIR LIVRET A"), Category(""), Account("1", "Main"), amount)
        t.is_internal = is_internal
        return t

    def test_show_cluster_tags_internal_transactions(self, capsys):
        cluster = TransactionCluster([self._transaction(-500.0, 5, True), self._transaction(-10.0, 20, False)])
        review = ClusterReview("cluster_0", cluster, ClusterMatch(ClusterStatus.UNGROUPED))

        bilig_cli.QuestionaryUi().show_cluster(review, Progress(0, 1, 0, 1))

        lines = capsys.readouterr().out.splitlines()
        [internal] = [line for line in lines if "2024-01-05" in line]
        [external] = [line for line in lines if "2024-01-20" in line]
        assert internal.endswith("[internal]")
        assert "[internal]" not in external
