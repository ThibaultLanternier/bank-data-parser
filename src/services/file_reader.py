from pathlib import Path


class FileReader:
    def __init__(self, path: str):
        self.path = Path(path)

    def get_csv_files(self) -> list[Path]:
        return sorted(self.path.rglob("*.csv"))

    def get_qif_files(self) -> list[Path]:
        return sorted(p for p in self.path.rglob("*") if p.suffix.lower() == ".qif")
