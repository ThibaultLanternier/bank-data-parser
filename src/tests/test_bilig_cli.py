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
