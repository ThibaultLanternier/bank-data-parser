import importlib.util
from pathlib import Path

import pytest
from click.testing import CliRunner

import services.file_recorder

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
"""

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
