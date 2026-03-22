from net import PetriNet

class Parser:
    """
    Classe che permette di fare il parsing della rete di Petri a partire dai file
    generati dal software "TINA"

    Args:

        path (string) = path/nome del file che contiene la rete di petri
    """
    def __init__(self, path):
        self.filePath = path
    
    def parse(self):
        """
        Funzione che scannerizza il file txt e chiama le funzioni per costruire
        la rete di Petri.

        Ogni linea/riga del file txt viene diviso attraverso il metodo split()
        In base alla prima lettera si capisce se si tratta di un place, di una transizione o di un arco:

            - p = place
            - t = transition
            - e = edge

        Viene fatto un controllo sulla riga, per vedere se si sta effettivamente utilizzando il formato di TINA, poi
        vengono ignorate le coordinate e agli altri elementi non utili alla costruzione della rete

        Args:

            net (PetriNet) = oggetto rete
        """
        net = PetriNet()

        with open(self.filePath) as f:
            for line in f:
                v = line.split()

                if not v:
                    continue
                if v[0] == "p":
                    if len(v) != 6:
                        raise ValueError("ERRORE: formato place non valido")
                    
                    _, _, _, name, tokens, _ = v
                    net.addPlace(name, int(tokens))
                elif v[0] == "t":
                    if len(v) != 7:
                        raise ValueError("ERRORE: formato transition non valido")
                    
                    _, _, _, name, _, _, _ = v
                    net.addTransition(name)
                elif v[0] == "e":
                    if len(v) != 5:
                        raise ValueError("ERRORE: formato arco non valido")
                    
                    _, source, destination, weight, _ = v
                    net.addArcs(source, destination, weight)
                elif v[0] == "h":
                    continue
                else:
                    raise ValueError("ERRORE: Tipo di riga sconosciuta")
        return net