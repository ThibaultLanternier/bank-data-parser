from pathlib import Path


class FileReader:
    def __init__(self, path: str):
        self.path = Path(path)

    def get_csv_files(self) -> list[Path]:
        return self._get_files("csv")

    def get_ofx_files(self) -> list[Path]:
        return self._get_files("ofx")

    def _get_files(self, extension: str) -> list[Path]:
        # Case insensitive, banks export both ".ofx" and ".OFX"
        return sorted(p for p in self.path.rglob("*") if p.is_file() and p.suffix.lower() == f".{extension}")
