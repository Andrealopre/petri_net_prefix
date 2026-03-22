class Place:
    """
    Classe che rappresenta un place della rete di Petri

    Args:

        name (string): nome del place

        tokens (int): numero di token presenti nel place
    """
    def __init__(self, name, tokens):
        self.name = name
        self.tokens = tokens

class Transition:
    """
    Classe che rappresenta una transizione della rete di Petri

    Args:

        name (string): nome della transizione
    """
    def __init__(self, name):
        self.name = name

class Arc:
    """
    Classe che rappresenta un arco della rete di Petri
    Può essere place -> Transition
    Oppure Transition -> Place

    Args:

        src (Place/Transition): source dell'arco

        dst (Place/Transition): destination dell'arco

        weight (int): peso dell'arco, assunto essere 1
    """
    def __init__(self, src, dst, weight = 1):
        self.src = src
        self.dst = dst
        self.weight = weight

class PetriNet:
    """
    Classe che rappresenta la rete di Petri intera. Utilizza le classi
    Place e Transition in delle strutture dati di tipo set() e li collega tramite gli archi

    Args:

        places (set()): insieme che contiene tutti i place della rete

        transition (set()): insieme che contiene tutte le transizioni della rete

        arcs (list): lista che contiene gli archi della rete
    """
    def __init__(self):
        self.places = {}
        self.transitions = {}
        self.arcs = []
    
    def addPlace(self, p_name, token):
        """
        Funzione che aggiunge un place alla rete, inserendolo nel set() places, usando il nome del
        place come key. In particolare al place in posizione key (places[p_name]) viene aggiunto un oggetto
        di tipo Place

        Args:

            p_name (string): nome del place

            token (int): numero di token presenti nel place
        """
        self.places[p_name] = Place(p_name, token)

    def addTransition(self, t_name):
        """
        Funzione che aggiunge una transition alla rete, inserendola nel set() transition, usando il nome della 
        transizione come key. Alla transizione in posizione key (transition[t_name]) viene aggiunto un oggetto
        di tipo Transition

        Args:

            t_name (string): nome della transizione
        """
        self.transitions[t_name] = Transition(t_name)
    
    #da reworkare
    def addArcs(self, src, dst, weight=1):
        """
        Funzione che aggiunge la relazione "arco" nella lista arcs, tra un place e una transizione e tra una 
        transizione e un place. Lo fa controllando se source si trova nei place e destination nelle transizioni, 
        oppure il contrario se l'arco va dalla transizione ad un place. 
        Genera un errore "arco non valido" in caso src e/o dst non esistanto, 
        ovvero se si cerca di aggiungere un arco tra due elementi inesistenti
        Inserisce nella relazione l'oggetto Place o Transition in base al nome

        Args:

            src (string): nome della source della relazione

            dst (string): nome della destinazione della relazione
        """
        if src in self.places and dst in self.transitions:
            self.arcs.append(Arc(self.places[src], self.transitions[dst], weight))
        elif src in self.transitions and dst in self.places:
            self.arcs.append(Arc(self.transitions[src], self.places[dst], weight))
        else:
            raise ValueError("Errore: arco non valido")
    
    def pasteNet(self):
        """
        Semplice funzione che stampa la rete. Stampa tutti i place, tutte le transizioni e tutte le relazioni di arco.
        Inoltre stampa in numero di token presenti in un place
        """
        for p in self.places:
            print("Posti inseriti:", p)
        
        for t in self.transitions:
            print("Transizioni inserite:", t)
        
        for x in self.arcs:
            print("Archi:", x.src, x.dst)
        
        for place_name, place_obj in self.places.items():
            print(f"{place_name} ha {place_obj.tokens} token")