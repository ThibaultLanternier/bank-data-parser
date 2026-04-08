from enum import Enum


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
        self.raw_label = raw_label

    def get_type(self) -> TransactionType:
        if "|" not in self.raw_label:
            return TransactionType.UNKNOWN

        raw_part = self.raw_label.split("|", 1)[1].strip().upper()

        for prefix, transaction_type in _TYPE_MAP:
            if raw_part.startswith(prefix):
                return transaction_type

        return TransactionType.UNKNOWN
