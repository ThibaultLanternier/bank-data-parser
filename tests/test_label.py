import pytest

from src.entities.label import Label, TransactionType


class TestGetLabel:
    def test_no_clean_label(self):
        label = Label("Carte 11/02/25 Uniqlo Opera Cb*6863 | CARTE 11/02/25 Uniqlo Opera CB*6863")
        assert label.get_label() == "Uniqlo Opera"

    def test_another_not_clean_label(self):
        label = Label("Carte 24/02/25 Lidl 2652 Cb*6863 | CARTE 24/02/25 LIDL 2652 CB*6863")
        assert label.get_label() == "Lidl"

    def test_label_with_avoir(self):
        label = Label("Avoir 22/06/22 Ikea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "Ikea"
    
    def test_label_with_avoir_upper_case(self):
        label = Label("AVOIR 22/06/22 Ikea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "Ikea"

    def test_label_with_useless_numbers(self):
        label = Label("Carte 20/05/22 35 Jus D Octobre Cb*3711 | CARTE 20/05/22 35 JUS D OCTOBRE  CB*3711")
        assert label.get_label() == "Jus D Octobre"

    def test_label_with_avoir_inside(self):
        label = Label("Avoir 22/06/22 AvoirIkea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "AvoirIkea"

    def test_label_with_sepa(self):
        label = Label("Rej Prlv Sepa Darty Grand Ouest | REJ PRLV SEPA DARTY GRAND OUEST")
        assert label.get_label() == "Darty Grand Ouest"

    def test_label_with_pipe(self):
        label = Label("PAYMENT | VIR SEPA 123456789")
        assert label.get_label() == "PAYMENT"

    def test_label_with_multiple_pipes(self):
        label = Label("First | Second | Third")
        assert label.get_label() == "First"

    def test_label_with_whitespace(self):
        label = Label("  Spaced label  ")
        assert label.get_label() == "Spaced label"

    def test_label_empty_string(self):
        label = Label("")
        assert label.get_label() == ""


class TestGetType:
    def test_type_vir_sepa(self):
        label = Label("PAYMENT | VIR SEPA 123456789")
        assert label.get_type() == TransactionType.VIR_SEPA

    def test_type_vir_inst(self):
        label = Label("TRANSFER | VIR INST 987654321")
        assert label.get_type() == TransactionType.VIR_INST

    def test_type_prlv_sepa(self):
        label = Label("DIRECT DEBIT | PRLV SEPA REF123")
        assert label.get_type() == TransactionType.PRLV_SEPA

    def test_type_rej_prlv_sepa(self):
        label = Label("REJECTED | REJ PRLV SEPA 456789")
        assert label.get_type() == TransactionType.REJ_PRLV_SEPA

    def test_type_rej_vir_inst(self):
        label = Label("REJECTED | REJ VIR INST 123456")
        assert label.get_type() == TransactionType.REJ_VIR_INST

    def test_type_carte(self):
        label = Label("PURCHASE | CARTE 14/04 ABC123")
        assert label.get_type() == TransactionType.CARD

    def test_type_retrait_dab(self):
        label = Label("ATM | RETRAIT DAB 500€")
        assert label.get_type() == TransactionType.RETRAIT_DAB

    def test_type_cheque(self):
        label = Label("CHECK | CHQ. 123456")
        assert label.get_type() == TransactionType.CHQ

    def test_type_avoir(self):
        label = Label("REFUND | AVOIR CREDIT")
        assert label.get_type() == TransactionType.AVOIR

    def test_type_ech_pret(self):
        label = Label("LOAN | ECH PRET 12345")
        assert label.get_type() == TransactionType.ECH_PRET

    def test_type_rem_chq(self):
        label = Label("DEPOSIT | REM CHQ 789012")
        assert label.get_type() == TransactionType.REM_CHQ

    def test_type_cion_cb_etr(self):
        label = Label("FOREIGN | *CION CB OP. ETR 456789")
        assert label.get_type() == TransactionType.CION_CB_ETR

    def test_type_cion_rapatriement(self):
        label = Label("REPATRIATION | *CION RAPATRIEMENT 123456")
        assert label.get_type() == TransactionType.CION_RAPATRIEMENT

    def test_type_inter_bruts(self):
        label = Label("INTEREST | *INTER.BRUTS 100.50")
        assert label.get_type() == TransactionType.INTER_BRUTS

    def test_type_prelevements_fiscaux(self):
        label = Label("TAX | *PRELEVEMENTS FISCAUX 250")
        assert label.get_type() == TransactionType.PRELEVEMENTS_FISCAUX

    def test_type_double_prelevements_fiscaux(self):
        label = Label("TAX | **PRELEVEMENTS FISCAUX 150")
        assert label.get_type() == TransactionType.PRELEVEMENTS_FISCAUX

    def test_type_prelevements_sociaux(self):
        label = Label("SOCIAL | PRELEVEMENT SOCIAUX 300")
        assert label.get_type() == TransactionType.PRELEVEMENTS_SOCIAUX

    def test_type_transfert(self):
        label = Label("TRANSFER | TDF EMIS VIA CB 789012")
        assert label.get_type() == TransactionType.TRANSFERT

    def test_type_unknown_without_pipe(self):
        label = Label("UNKNOWN TRANSACTION")
        assert label.get_type() == TransactionType.UNKNOWN

    def test_type_unknown_no_match(self):
        label = Label("PAYMENT | SOMETHING ELSE")
        assert label.get_type() == TransactionType.UNKNOWN


class TestGetCreditCardNumber:
    def test_card_number_found(self):
        label = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        assert label.get_credit_card_number() == "*3657"

    def test_card_number_not_found_no_pipe(self):
        label = Label("Prlv Sepa Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE")
        assert label.get_credit_card_number() is None