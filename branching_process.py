import json
from collections import defaultdict, deque
import collections

class Condition:
    """
    Classe condizione, rappresenta un place e l'evento che lo genera
    """
    _counter = 1 # contatore della condizione, usato come "id"
    def __init__(self, place, input_event=None):
        """
        Costruttore della condizione
        """
        self.place = place
        self.event = input_event
        self.id = Condition._counter
        Condition._counter += 1
    
    def __eq__(self, other):
        """
        Metodo per valutare l'uguaglianza con un altra condizione
        ritorna true se le due condizioni sono uguali, se hanno stesso place e stesso evento
        """
        if not isinstance(other, Condition):
            return False
        return self.place == other.place and self.event == other.event
    
    def __hash__(self):
        """
        Metodo per trovare l'hash della condizione
        """
        ev_id = self.event.id if self.event is not None else -1
        return hash((self.place, ev_id))
    
    def __repr__(self):
        """
        Rappresentazione sotto forma di strigna della condizione
        """
        return f"C({self.place.name}, {self.event.transition.name if self.event else 'init'})"


class Event:
    """
    Classe evento
    Rappresenta una transizione, le sue condizioni di input e mantiene in memoria anche le condizioni
    di output
    """
    _counter = 1 # contatore dell'evento, usato come Id per tale evento
    
    def __init__(self, transition, input_conditions):
        """
        Costruttore della classe Event
        """
        self.transition = transition
        self.input_conditions = set(input_conditions)
        self.output_conditions = set()

        self.id = Event._counter
        Event._counter += 1
        """
        L'id di ogni evento si basa sulla variabile globale della classe Event: _counter. Viene incrementato ogni
        volta che un nuovo evento è creato
        """
    
    def __eq__(self, other):
        """
        Metodo per valutare uguaglianza con altro Evento
        """
        return isinstance(other, Event) and self.id == other.id
    
    def __hash__(self):
        """Ritorna l'hash dell'evento"""
        input_hashes = frozenset(c.place.name for c in self.input_conditions)
        return hash(self.id)
    
    def __repr__(self):
        """Ritorna la stringa di rappresentazione dell'evento"""
        return f"E({self.transition.name}, #{self.id})"

class Processor:
    """
    Classe processor. La classe principale del branching process.
    Il suo compito è di generare l'unfolding della rete
    Prende in input la rete di Petri su cui si sta lavorando
    """
    def __init__(self, net):
        """
        Costruttore della classe Processor
        """
        self.net = net
        self.min = set()

        self.events = set()
        self.conditions = set()
        # Event e Conditions hanno solamente eventi e condizioni inseriti nell'unfolding

        self.conflict_relation = set()
        self.causal_relation_pre = set()
        self.causal_relation_post = set()

        self.cut_off = set()

        self.min_by_marking = {}
        self.config_cache = {}
        self.config_length_cache = {}

    def unfolding_algorithm(self):
        """
        Funzione principale dell'algoritmo di unfolding. Inizializza unf e pe e poi comincia il ciclo 
        principale, estraendo l'evento minimo da PE, aggiungendolo all'unfolding e poi controllando se si tratti di
        un evento cut-off
        """

        # Inizializzazione di unf e pe
        unf = set(self.initialMarking())

        if not unf:
            raise("ERRORE: la rete non ha una marcatura iniziale")

        pe = self.initial_extensions(unf)

        initial_marking = frozenset(c.place.name for c in self.min)
        self.min_by_marking[initial_marking] = None

        while pe: # inizio ciclo
            
            candidate_event = self.get_minimal_event(pe)
            pe.remove(candidate_event)
            print(f"Evento: {candidate_event.transition.name}")
            unf.add(candidate_event) 
            self.events.add(candidate_event)

            for cond in candidate_event.output_conditions:
                unf.add(cond)
                self.conditions.add(cond)
                self.causal_updater_post(candidate_event, cond)
            
            for cond in candidate_event.input_conditions:
                self.causal_updater_pre(cond, candidate_event)

            is_cut = self.is_cutoff(candidate_event)
            
            if not is_cut:
                self.update_conflict_relation(candidate_event)
                extensions = self.update_pot_ext({c for c in unf if isinstance(c, Condition)}, candidate_event)
                pe |= extensions
                
            else:
                self.update_conflict_relation(candidate_event)
                self.cut_off.add(candidate_event)
                print(f"Cutoff trovato: {candidate_event.transition.name} - #evento {candidate_event.id}")
        
        return unf


    def local_configuration(self, event):
        if event in self.config_cache:
            return self.config_cache[event]
        
        visited = set()
        stack = [event]

        while stack:
            node = stack.pop()

            if node in visited:
                continue

            visited.add(node)

            for c in node.input_conditions:
                if c.event is not None:
                    stack.append(c.event)
        
        self.config_cache[event] = visited
        return visited
    
    def get_config_length(self, event):
        if event in self.config_length_cache:
            return self.config_length_cache[event]
        
        length = len(self.local_configuration(event))
        self.config_length_cache[event] = length
        return length

    def get_foata_normal_form(self, config):
        config_set = set(config)
        foata_form = []

        while config_set:
            min_elements = []

            # Trova eventi senza predecessori
            for e in config_set:
                has_predecessor = False

                for c in e.input_conditions:
                    if c.event is not None and c.event in config_set:
                        has_predecessor = True
                        break
                
                if not has_predecessor:
                    min_elements.append(e)
            
            if not min_elements:
                # non dovrebbe accadere
                print(f"Nessun elemento minimale trovato - config rimanente: {config_set}")
                break
            
            min_elements.sort(key=lambda x: id(x.transition) if x.transition else 0)

            slice_vector = tuple(id(e.transition) if e.transition else 0 for e in min_elements)
            foata_form.append(slice_vector)

            for e in min_elements:
                config_set.remove(e)
        return tuple(foata_form)

    def compare_adequate_order(self, ev1, ev2):
        # Primo livello: confronto per dimensione della configurazione
        len1 = self.get_config_length(ev1)
        len2 = self.get_config_length(ev2)

        if len1 != len2:
            return -1 if len1 < len2 else 1
        
        # Secondo livello: Confronto se un evento si trovi prima dell'altro, usando i loro id
        config1 = self.local_configuration(ev1)
        config2 = self.local_configuration(ev2)

        #sortedId1 = tuple(sorted(e.id for e in config1))
        #sortedId2 = tuple(sorted(e.id for e in config2))

        #if sortedId1 != sortedId2:
            #return -1 if sortedId1 < sortedId2 else 1
        
        sortedLabels1 = tuple(sorted(id(e.transition) if e.transition else 0 for e in config1))
        sortedLabels2 = tuple(sorted(id(e.transition) if e.transition else 0 for e in config2))

        if sortedLabels1 != sortedLabels2:
            return -1 if sortedLabels1 < sortedLabels2 else 1
        
        # Terzo livello: confronto con la forma normale di foata
        foata1 = self.get_foata_normal_form(config1)
        foata2 = self.get_foata_normal_form(config2)

        if foata1 < foata2:
            return -1
        if foata1 > foata2:
            return 1
        
        return 0
    
    def calculate_cut(self, config):
        c_preset = set()
        c_postset = set()

        for event in config:
            c_preset |= event.input_conditions
            c_postset |= event.output_conditions
        
        unused_initial = self.min - c_preset

        cut = (unused_initial | c_postset) - c_preset

        return cut

    def get_marking(self, event):
        config = self.local_configuration(event)
        cut = self.calculate_cut(config)
        
        marking = frozenset(c.place.name for c in cut if isinstance(c, Condition))
        return marking
    
    def is_cutoff(self, new_event):
        event_marking = self.get_marking(new_event)

        if event_marking in self.min_by_marking:
            min_event = self.min_by_marking[event_marking]

            if min_event is None:
                return True

            compare_result = self.compare_adequate_order(min_event, new_event)

            if compare_result < 0:
                return True
            elif compare_result > 0:
                self.min_by_marking[event_marking] = new_event
                return False
            else:
                return False
        self.min_by_marking[event_marking] = new_event
        return False

    def get_minimal_event(self, possible_extensions):
        from functools import cmp_to_key
        def compare(e1, e2):
            return self.compare_adequate_order(e1, e2)
        
        return min(possible_extensions, key=cmp_to_key(compare))

    def initialMarking(self):
        """
        Funzione che genera la marcatura iniziale della rete. Cerca tutti i place della rete di Petri, se il Place
        in considerazione ha un numero di token > 0, allora viene creata una nuova condizione e questa viene aggiunta
        all'insieme self.min, che indica la marcatura iniziale
        """
        for place_name, place_obj in self.net.places.items():
            if place_obj.tokens > 0: # se il numero di token > 0
                new_condition = Condition(place_obj) # creo la condizione
                self.conditions.add(new_condition) # possibilmente da togliere
                self.min.add(new_condition) #a aggiungo la nuova condizione a min
        
        return self.min

    def causal_updater_pre(self, condition, event):
        """
        Aggiunge la relazione causale condition -> event all'insieme causal_relation_pre
        """
        self.causal_relation_pre.add((condition, event))

    def causal_updater_post(self, event, condition):
        """
        Aggiunge la relazione causale event -> condition all'insieme causal_relation_post
        """
        self.causal_relation_post.add((event, condition))

    def initial_extensions(self, unf):
        """
        La funzione che trova le possible extensions iniziali.
        Incomincia prendendo tutte le condizioni dall'unfolding parziale passato come parametro. Successivamente
        cicla ogni transizione presente nella rete di Petri iniziale e, per ogni transizione, ne trova il preset.
        Vengono cercate le in_conditions, ovvero le condizioni di input da cui l'evento della transizione viene
        generato. Si controlla se la lunghezza delle in_conditions sia uguale a quella dei preset_places, in caso
        affermativo si crea il nuovo evento (new_event(t, in_conditions)) e viene aggiunto alle initial_extensions
        """
        initial_extensions = set()

        # vengono prese tutte le condizioni in unf, possibilmente inutile, dato che si stanno trattando solo
        # le initial_extensions, ma mai essere sicuri
        initial_markings = {c for c in unf if isinstance(c, Condition)}

        # ciclo for per ogni transizione t presente nella rete di Petri
        for t in self.net.transitions.values():

            # cerco i preset della transizione.
            preset_places = self.find_preset(t)

            # inserisco le condizioni di input il cui place è presente nei preset_places della transizione t
            in_conditions = {c for c in initial_markings if c.place in preset_places}

            if len(in_conditions) == len(preset_places):
                new_event = Event(t, in_conditions) #creo il nuovo evento

                # cerco i place successivi alla transizione e creo la condizione, inserendole nelle output_conditions
                # dell'evento appena creato
                post_places = {arc.dst for arc in self.net.arcs if arc.src == t}

                for p in post_places:
                    new_condition = Condition(p, new_event)
                    new_event.output_conditions.add(new_condition)
                
                initial_extensions.add(new_event)       

        return initial_extensions
    
    def update_pot_ext(self, unf, e):
        """
        Funzione update_pot_ext ispirata dalla (quasi)medesima funzione presentata da Victor Khomenko nella sua tesi di
        dottorato. Si occupa di filtrare le transizioni successive tramite le euristiche spiegate nella tesi. Dopo
        cicla per ogni transizione, trova il preset della transizione considerata e trova tutte le condizioni c
        presenti nell'unfolding che sono nel preset di t e che siano concorrenti con l'evento e iniziale.
        Successivamente chiama la funzione cover.
        """
        
        extensions = set()
        
        # Prendo la transizione etichettata dall'evento e
        u = e.transition
        
        post_places = self.find_post_places(u)  # u*
        succ_transitions = self.find_succ_transitions(post_places)  # (u*)*

        preset_places = self.find_preset(u)  # *u

        difference = preset_places - post_places  # (*u \ u*)

        post_difference = self.find_difference(difference)  # (*u \ u*)* postset della differenza

        transitions = succ_transitions - post_difference  # (u*)* \ (*u \ u*)*
        
        # cicla tutte le transizioni t nelle transizioni possibili
        for t in transitions:
            preset = self.find_preset(t)  # trova il preset di t

            # ciclo che aggiunge a C le condizioni di unf, concorrenti all'evento e
            C = {c for c in unf if isinstance(c, Condition) and c.place in preset and self.is_concurrent(c, e)}

            extensions |= self.cover(C, t, dict())  # estende le estensioni grazie alla funzione di supporto cover

        return extensions
    


    def cover(self, C, t, preset):
        """
        Funzione che serve a completare il preset di un evento candidato.
        Controlla le condizioni concorrenti e sceglie quelle che possono formare un preset
        per una possibile estensione
        """
        pre_t = self.find_preset(t)
        extensions = set()

        # se il preset è completo, ovvero se è uguale alla cardinalità di *t entra 
        # nell'if
        if len(pre_t) == len(preset): # caso base

            # trova le input_conditions in preset che si trovano nel 
            # preset di t
            in_conditions = {preset[p] for p in pre_t}

            condition_list = list(in_conditions)
            for i in range(len(condition_list)):
                for j in range(i + 1, len(condition_list)):
                    if not self.is_concurrent(condition_list[i], condition_list[j]):
                        return set()

            # se esiste già un evento uguale nell'unfolding, non si creanno duplicati
            # ma si utilizza l'evento già inserito
            existing = self.existing_event(t, in_conditions)
            if existing:
                #return {existing} # ritorna evento già esistente
                return set()

            # altrimenti si crea un nuovo evento
            new_event = Event(t, in_conditions)

            # qui si trovano i posti successivi alla transizione t
            # sono le output conditions
            postset_places = {arc.dst for arc in self.net.arcs if arc.src == t}

            for place in postset_places:
                new_condition = Condition(place, new_event)
                new_event.output_conditions.add(new_condition)

            # si espandono le estensioni e si ritorna
            extensions.add(new_event)
            return extensions
        else: # passo ricorsivo

            # scelgo un place nel preset NON ancora presente nel preset che sto
            # costruendo
            diff = pre_t - set(preset.keys())

            p = next(iter(diff))

            # ciclo le condizioni in C e seleziono quelle che hanno il place uguale a quello scelto precedentemente
            for d in [cond for cond in C if cond.place == p]:
                # aggiungo a C_first (C') le condizioni in C concorrenti con la condizione d
                C_first = {c for c in C if self.is_concurrent(c, d)}

                # incremento il preset in costruzione
                union_preset = dict(preset)
                union_preset[p] = d

                # estendo con chiamata ricorsiva
                extensions |= self.cover(C_first, t, union_preset)

            return extensions
    
    def add_conflict(self, e1, e2):
        """
        Funzione che aggiunge gli eventi alla conflict_relation
        """
        self.conflict_relation.add((e1, e2))
        self.conflict_relation.add((e2, e1))

    def update_conflict_relation(self, event):
        """
        Funzione che aggiorna le relazioni di conflitto tra l'evento passato in input e tutti gli eventi presenti
        nell'unfolding.
        Controlla ogni evento presente in self.events (che contiene solo gli eventi già presenti nell'unfolding).
        Propaga il conflitto agli eventi delle input conditions
        """

        for e in self.events:

            # se "e" è l'evento stesso, continua
            if e is event:
                continue

            # se la relazione di conflitto è già presente continua
            if (event, e) in self.conflict_relation or (e, event) in self.conflict_relation:
                continue

            # se i preset di event e di "e" non hanno elementi in comune, aggiunge gli eventi nel conflitto
            if not event.input_conditions.isdisjoint(e.input_conditions):
                self.add_conflict(event, e)
            
            # Se gli eventi delle input conditions di event sono in conflitto con l'evento e, allora anche event
            # sarà in conflitto con l'evento e
            for c in event.input_conditions:
                if c.event and ((c.event, e) in self.conflict_relation or (e, c.event) in self.conflict_relation):
                    self.add_conflict(event, e)
                    break

    def find_post_places(self, transition):
        """
        Funzione che trova i posti nel postset della transizione t
        """
        post_places = set()

        # Cerca tutti gli archi nella rete, se la source equivale alla transizione, aggiunge il place nel postset
        for arc in self.net.arcs:
            if arc.src == transition:
                post_places.add(arc.dst)

        return post_places

    def find_succ_transitions(self, p_places):
        """
        Funzione che trova le transizione successive a p_places
        """
        succ_transitions = set()

        for arc in self.net.arcs:
            for p in p_places:
                if arc.src == p:
                    succ_transitions.add(arc.dst)
        
        return succ_transitions
    
    def find_preset(self, transition):
        """
        Trova il preset della transizione passata come parametro
        """
        preset = set()

        for arc in self.net.arcs:
            if arc.dst == transition:
                preset.add(arc.src)
        
        return preset

    def find_difference(self, difference):
        """
        Trova il postset di (*u - u*) ovvero (*u - u*)*
        Se è presente una source nell'insieme degli archi, che equivale ad un posto p nell'insieme di (*u - u*), allora
        la sua destination viene salvata.
        """
        post_difference = set()

        for arc in self.net.arcs:
            for p in difference:
                if arc.src == p:
                    post_difference.add(arc.dst)
        
        return post_difference
   
    def is_causal(self, x, y):
        """
        Algoritmo BFS per controllare la causalità di due argomenti passati in input.
        Se x e y sono condizioni, vengono rese eventi. Se sono condizioni iniziali, allora False.
        Se sono lo stesso evento -> False
        Se, ciclando per tutta la "linea" causale si trova l'evento y, allora ritorna True
        """

        # Ottengo gli eventi di x e y se sono condizioni, altrimenti lascia invariato
        x_ev = x.event if isinstance(x, Condition) else x
        y_ev = y.event if isinstance(y, Condition) else y

        # Se uno dei due eventi è nullo, allora non c'è causalità
        if x_ev is None or y_ev is None:
            return False
        
        # se gli eventi sono gli stessi PRIMA del ciclo, allora non sono causali
        if x_ev is y_ev:
            return False
        
        # inizializza un set di nodi visitati e una lista che parte dall'evento x
        visited = set()
        cone = [x_ev]

        # estrae un nodo da cone, se node == y allora vuol dire che si è trovato y tra i successori
        # e quindi c'è causalità
        while cone:
            node = cone.pop() # prende il primo elemento da cone e lo assegna a node

            if node == y_ev: # nodo y trovato nei successori
                return True
            
            # se il nodo è visitato continua
            # aggiunge node a visited e crea il set di successori, che andranno ad estendere il cono
            if node in visited:
                continue
            visited.add(node)

            # condizioni prodotte dal nodo preso in considerazione
            produced_conditions = {cond for (e, cond) in self.causal_relation_post if e is node}

            # eventi successivi alle condizioni prodotte
            successor_events = {ev2 for (cond2, ev2) in self.causal_relation_pre if cond2 in produced_conditions}

            # estende il cono con i successor events
            cone.extend(successor_events)
        
        # se y non è trovato ritorna falso
        return False

    def node_to_event(self, node):
        """
        Funzione di comodo per ottenere l'evento di un nodo, se condizione
        Usare solo per is_concurrent()
        """
        if isinstance(node, Condition):
            return node.event
        return node

    def is_concurrent(self, n1, n2):
        """
        Funzione che controlla la concorrenza tra due eventi n1 e n2 passati input. La concorrenza è calcolata
        "al volo", controllando la presenza di causalità e conflitti.
        """

        # se n1 è n2 allora non sono concorrenti
        if n1 is n2:
            return False
        
        # ottengo gli eventi dei nodi, se sono condizioni
        e1 = self.node_to_event(n1)
        e2 = self.node_to_event(n2)
        
        if e1 is None and e2 is None:
            return True
            
        if e1 is None or e2 is None:
            if e1 is None:
                if n1 in e2.input_conditions:
                    return False
                config_e2 = self.local_configuration(e2)
                for ancestor_event in config_e2:
                    if n1 in ancestor_event.input_conditions:
                        return False
                return True
            else:
                if n2 in e1.input_conditions:
                    return False
                
                config_e1 = self.local_configuration(e1)
                for ancestor_event in config_e1:
                    if n2 in ancestor_event.input_conditions:
                        return False
                return True
                

        # check causalità
        if self.is_causal(e1, e2) or self.is_causal(e2, e1):
            return False

        # check conflitto
        if (e1, e2) in self.conflict_relation or (e2, e1) in self.conflict_relation:
            return False
        
        # se passa tutti i check c'è concorrenza
        return True
  
    def existing_event(self, t, input_conditions):
        """
        Funzione per controllare se un evento è già presente nell'unfolding.
        Controlla se la transizione sia la stessa e se abbiano le stesse condizioni di input.
        """
        for e in self.events:
            if e.transition == t and e.input_conditions == input_conditions:
                return e
        
        return None

    def print_unfolding(self, unf):
        """
        Funzione che stampa lo stato dell'unfolding.
        Stampa ogni evento e le sue input e output conditions.
        """
        print("Stato dell'unfolding")

        starting_conditions = []
        events = []

        # raggruppa tutte le condizioni senza evento, ovvero le condizioni iniziali
        for n in unf:
            if isinstance(n, Condition) and n.event == None:
                starting_conditions.append(n)
        
        # raggruppa tutti gli eventi presenti nell'unfolding
        for n in unf:
            if isinstance(n, Event):
                events.append(n)
        
        # stampa condizioni iniziali
        print("\nCondizioni iniziali")
        for c in starting_conditions:
            print(c.place.name, "", end="")

        # stampa degli eventi, con input e output conditions
        print("\nEventi")
        for e in events:
            input_names = []
            output_names = []

            for c in e.input_conditions:
                input_names.append(c.place.name)
            for c in e.output_conditions:
                output_names.append(c.place.name)

            print(f"Evento {e.transition.name}")
            print(f"Input: {input_names}")
            print(f"Output: {output_names}")
        
        condizioni_finali = []

        # raggruppa tutte le condizioni finali dell'unfolding
        for c in unf:
            if isinstance(c, Condition) and c not in starting_conditions and not any(c in ev.input_conditions for ev in events):
                condizioni_finali.append(c)
        
        # stampa delle condizioni finali
        print("\nCondizioni")
        for c in condizioni_finali:
            print(c.place.name)

    def file_to_dot(self, unf, filename="graph.dot"):
        graph = defaultdict(list)
        nodes_in_unf = set(n for n in unf)
        cond_map = list()
        ev_map = list()
        elements_characteristics = list()

        for (cond, ev) in self.causal_relation_pre:
            if cond in nodes_in_unf and ev in nodes_in_unf:
                graph[cond].append(ev)
                cond_map.append(f"c{cond.id} -> e{ev.id};")
    
        for (ev, cond) in self.causal_relation_post:
            if ev in nodes_in_unf and cond in nodes_in_unf:
                graph[ev].append(cond)
                ev_map.append(f"e{ev.id} -> c{cond.id};")

        for n in nodes_in_unf:
            if isinstance(n, Condition):
                elements_characteristics.append(f'c{n.id} [label="{n.place.name} (c{n.id})" shape=circle];')
            if isinstance(n, Event):
                elements_characteristics.append(f'e{n.id} [label="{n.transition.name} (e{n.id})" shape=box];')
        
        with open(filename, "w") as f:
            f.write("digraph test {\n")
            for c in cond_map:
                f.write(f"{c}\n")
            for e in ev_map:
                f.write(f"{e}\n")
            
            for e in elements_characteristics:
                f.write(f"{e}\n")
            f.write("}\n")