from services.file_reader import FileReader


class TestFileReader:
    def test_finds_files_by_extension(self, tmp_path):
        (tmp_path / "sub").mkdir()
        for name in ["a.csv", "sub/b.CSV", "c.ofx", "sub/d.OFX", "f.qif", "sub/g.QIF", "e.txt"]:
            (tmp_path / name).write_text("")

        reader = FileReader(str(tmp_path))

        assert reader.get_csv_files() == [tmp_path / "a.csv", tmp_path / "sub/b.CSV"]
        assert reader.get_ofx_files() == [tmp_path / "c.ofx", tmp_path / "sub/d.OFX"]
        assert reader.get_qif_files() == [tmp_path / "f.qif", tmp_path / "sub/g.QIF"]
