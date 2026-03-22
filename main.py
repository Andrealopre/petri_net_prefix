from net import PetriNet
from parser import Parser
from branching_process import Processor
import time
import sys

def main(filepath):
    net = PetriNet()
    parser = Parser(filepath)
    
    net = parser.parse()
    processor = Processor(net)

    unf = processor.unfolding_algorithm()
    processor.print_unfolding(unf)

    substring = ".ndr"
    filename_dot = filepath.split(substring)[0]
    filename_dot = filename_dot + ".dot"
    processor.file_to_dot(unf, filename_dot)

if __name__ == "__main__":
    start_time = time.time()
    filepath = sys.argv[1] 
    main(filepath)
    print(f"--- Secondi: {time.time() - start_time}")