from services.file_reader import FileReader


class TestFileReader:
    def test_get_qif_files(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "b.qif").touch()
        (tmp_path / "sub" / "a.QIF").touch()
        (tmp_path / "c.csv").touch()

        files = FileReader(str(tmp_path)).get_qif_files()

        assert files == sorted([tmp_path / "b.qif", tmp_path / "sub" / "a.QIF"])

    def test_get_csv_files_ignores_qif(self, tmp_path):
        (tmp_path / "b.qif").touch()
        (tmp_path / "c.csv").touch()

        assert FileReader(str(tmp_path)).get_csv_files() == [tmp_path / "c.csv"]
