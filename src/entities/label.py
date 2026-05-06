from math import e
import re
from enum import Enum
import unicodedata

from rapidfuzz import fuzz

class TransactionType(Enum):
    CARD = "CARD"
    VIR = "VIR"
    VIR_SEPA = "VIR SEPA"
    VIR_INST = "VIR INST"
    PRLV_SEPA = "PRLV SEPA"
    RETRAIT_DAB = "RETRAIT DAB"
    CHQ = "CHQ"
    AVOIR = "AVOIR"
    ECH_PRET = "ECH PRET"
    REJ_PRLV_SEPA = "REJ PRLV SEPA"
    REJ_VIR_INST = "REJ VIR INST"
    REM_CHQ = "REM CHQ"
    CION_CB_ETR = "*CION CB OP. ETR"
    CION_RAPATRIEMENT = "*CION RAPATRIEMENT"
    INTER_BRUTS = "*INTER.BRUTS"
    PRELEVEMENTS_FISCAUX = "*PRELEVEMENTS FISCAUX"
    PRELEVEMENTS_SOCIAUX = "PRELEVEMENT SOCIAUX"
    TRANSFERT = "TDF EMIS VIA CB"
    UNKNOWN = "UNKNOWN"


# Checked in order: longer/more specific prefixes must come before shorter ones
_TYPE_MAP = [
    ("VIR SEPA", TransactionType.VIR_SEPA),
    ("VIR INST", TransactionType.VIR_INST),
    ("REJ PRLV SEPA", TransactionType.REJ_PRLV_SEPA),
    ("PRLV SEPA", TransactionType.PRLV_SEPA),
    ("RETRAIT DAB", TransactionType.RETRAIT_DAB),
    ("REM CHQ", TransactionType.REM_CHQ),
    ("ECH PRET", TransactionType.ECH_PRET),
    ("AVOIR", TransactionType.AVOIR),
    ("*CION CB OP. ETR", TransactionType.CION_CB_ETR),
    ("*CION RAPATRIEMENT", TransactionType.CION_RAPATRIEMENT),
    ("*INTER.BRUTS", TransactionType.INTER_BRUTS),
    ("*PRELEVEMENTS FISCAUX", TransactionType.PRELEVEMENTS_FISCAUX),
    ("**PRELEVEMENTS FISCAUX", TransactionType.PRELEVEMENTS_FISCAUX),
    ("PRELEVEMENT SOCIAUX", TransactionType.PRELEVEMENTS_SOCIAUX),
    ("TDF EMIS VIA CB", TransactionType.TRANSFERT),
    ("REJ VIR INST", TransactionType.REJ_VIR_INST),
    ("CHQ.", TransactionType.CHQ),
    ("CARTE", TransactionType.CARD),
    ("VIR", TransactionType.VIR),
]


class Label:
    def __init__(self, raw_label: str):
        self.raw_label = raw_label.lower() # But in lowercase from the start

    def _get_label_part(self, part: int) -> str:
        if "|" not in self.raw_label:
            return self.raw_label.strip()

        parts = self.raw_label.split("|", 1)
        if part < len(parts):
            return parts[part].strip()
        else:
            return ""
    
    def _remove_date(self, label: str) -> str:
        return re.sub(r"\b\d{2}/\d{2}/\d{2}\b", "", label)
    
    def remove_card_number(self, label: str) -> str:
        return re.sub(r"cb\*\d+", "", label)
    
    def remove_keywords(self, label: str) -> str:
        keywords = ["CARTE", "AVOIR", "VIR", "SEPA", "INST", "PRLV", "REJ"]

        label_elements = label.split()

        elements_to_keep = []

        for element in label_elements:
            if element.upper() not in keywords:
                elements_to_keep.append(element)

        return " ".join(elements_to_keep)
    
    def remove_numbers(self, label: str) -> str:
        label_elements = label.split()

        elements_to_keep = []

        for element in label_elements:
            if not re.match(r"^\d+$", element):
                elements_to_keep.append(element)
        
        return " ".join(elements_to_keep)

    def get_label(self) -> str:
        clean_label = self._get_label_part(0)
        clean_label = self._remove_date(clean_label)
        clean_label = self.remove_card_number(clean_label)
        clean_label = self.remove_keywords(clean_label)
        clean_label = self.remove_numbers(clean_label)

        return clean_label.strip()
    
    def get_normalized_label(self) -> str:
        s = self.get_label()
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        s = re.sub(r'[._\-]', ' ', s)
        s = re.sub(r'\b(com|www|inc|llc|ab)\b', '', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def get_credit_card_number(self) -> str | None:
        if "|" not in self.raw_label:
            return None

        raw_part = self._get_label_part(1)
        match = re.search(r"cb\*(\d+)$", raw_part)
        if match:
            return f"*{match.group(1)}"

        return None

    def get_type(self) -> TransactionType:
        if "|" not in self.raw_label:
            return TransactionType.UNKNOWN

        raw_part = self._get_label_part(1).upper()

        for prefix, transaction_type in _TYPE_MAP:
            if raw_part.startswith(prefix):
                return transaction_type

        return TransactionType.UNKNOWN
    
    def get_similarity(self, other: 'Label') -> float:
        similarity = fuzz.token_sort_ratio(self.get_normalized_label(), other.get_normalized_label()) / 100.0
        return similarity