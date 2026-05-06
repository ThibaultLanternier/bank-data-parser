import pytest

from entities.label import Label,TransactionType

class TestGetLabel:
    def test_no_clean_label(self):
        label = Label("Carte 11/02/25 Uniqlo Opera Cb*6863 | CARTE 11/02/25 Uniqlo Opera CB*6863")
        assert label.get_label() == "uniqlo opera"

    def test_another_not_clean_label(self):
        label = Label("Carte 24/02/25 Lidl 2652 Cb*6863 | CARTE 24/02/25 LIDL 2652 CB*6863")
        assert label.get_label() == "lidl"

    def test_label_with_avoir(self):
        label = Label("Avoir 22/06/22 Ikea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "ikea"
    
    def test_label_with_avoir_upper_case(self):
        label = Label("AVOIR 22/06/22 Ikea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "ikea"

    def test_label_with_useless_numbers(self):
        label = Label("Carte 20/05/22 35 Jus D Octobre Cb*3711 | CARTE 20/05/22 35 JUS D OCTOBRE  CB*3711")
        assert label.get_label() == "jus d octobre"

    def test_label_with_avoir_inside(self):
        label = Label("Avoir 22/06/22 AvoirIkea 2 Cb*1643 | AVOIR 22/06/22 IKEA            2 CB*1643")
        assert label.get_label() == "avoirikea"

    def test_label_with_sepa(self):
        label = Label("Rej Prlv Sepa Darty Grand Ouest | REJ PRLV SEPA DARTY GRAND OUEST")
        assert label.get_label() == "darty grand ouest"

    def test_label_with_pipe(self):
        label = Label("PAYMENT | VIR SEPA 123456789")
        assert label.get_label() == "payment"

    def test_label_with_multiple_pipes(self):
        label = Label("First | Second | Third")
        assert label.get_label() == "first"

    def test_label_with_whitespace(self):
        label = Label("  Spaced label  ")
        assert label.get_label() == "spaced label"

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

class TestGetNormalizedLabel:
    def test_normalized_label(self):
        label = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        assert label.get_normalized_label() == "grain de delice"

    def test_normalized_label_with_punctuation(self):
        label = Label("Prlv Sepa Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE")
        assert label.get_normalized_label() == "direction generale des finance"

    def test_normalized_label_with_keywords(self):
        label = Label("Avoir 30/10/24 Amzn Mktp Fr 169, Cb*3657 | AVOIR 30/10/24 AMZN Mktp FR 169, CB*3657")
        assert label.get_normalized_label() == "amzn mktp fr 169,"

    def test_normalized_label_1(self):
        label1 = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        label2 = Label("CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657 | Carte 12/07/25 Grain De Delice 4 Cb*3657")

        assert label1.get_normalized_label() == label2.get_normalized_label()

class TestGetCreditCardNumber:
    def test_card_number_found(self):
        label = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        assert label.get_credit_card_number() == "*3657"

    def test_card_number_not_found_no_pipe(self):
        label = Label("Prlv Sepa Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE")
        assert label.get_credit_card_number() is None

class TestSimilarity:
    def test_similarity(self):
        label1 = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        label2 = Label("CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657 | Carte 12/07/25 Grain De Delice 4 Cb*3657")
        assert label1.get_similarity(label2) == 1.0

    def test_similarity_different_labels(self):
        label1 = Label("Carte 12/07/25 Grain De Delice 4 Cb*3657 | CARTE 12/07/25 GRAIN DE DELICE 4 CB*3657")
        label2 = Label("Prlv Sepa Direction Generale Des Finance | PRLV SEPA DIRECTION GENERALE DES FINANCE")
        assert label1.get_similarity(label2) < 0.6

    def test_similarity_with_keywords(self):
        label1 = Label("Avoir 30/10/24 Amzn Mktp Fr 169, Cb*3657 | AVOIR 30/10/24 AMZN Mktp FR 169, CB*3657")
        label2 = Label("Avoir 01/12/23 Amzn Mktp Fr 11,3 Cb*6863 | AVOIR 01/12/23 AMZN Mktp FR 11,3 CB*6863")
        assert label1.get_similarity(label2) > 0.8

    def test_similarity_with_carrick_vs_air_france(self):
        label1 = Label("Carte 19/09/23 Carrick France Cb*6863 | CARTE 19/09/23 CARRICK FRANCE CB*6863")
        label2 = Label("Carte 14/07/23 Air France 05723 Cb*3657 | CARTE 14/07/23 AIR FRANCE 05723 CB*3657")
        assert label1.get_similarity(label2) >= 0.75

    def test_similarity_with_saint_malo(self):
        label1 = Label("Carte 03/03/22 Kiabi Saint Malo Cb*1643 | CARTE 03/03/22 KIABI SAINT MALO  CB*1643")
        label2 = Label("Carte 26/08/25 St Malo Debloque2 Cb*3657 | CARTE 26/08/25 ST MALO DEBLOQUE2 CB*3657")
        assert label1.get_similarity(label2) < 0.6
    
    def test_similarity_with_saint_malo_other(self):
        label1 = Label("Carte 17/07/25 Au Pain St Malo Cb*6863 | CARTE 17/07/25 AU PAIN ST MALO CB*6863")
        label2 = Label("Carte 26/08/25 St Malo Debloque2 Cb*3657 | CARTE 26/08/25 ST MALO DEBLOQUE2 CB*3657")
        assert label1.get_similarity(label2) < 0.6