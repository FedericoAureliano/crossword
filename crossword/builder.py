# Code started with https://bohlender.pro/blog/generating-crosswords-with-sat-smt/ but has changed a lot since then

import z3

from crossword.utils import print_time
from crossword.constants import ACROSS, DOWN, BLANK
from crossword.crossword import Crossword

from timeit import default_timer as timer

class GridBuilder:
    @print_time("Setup")
    def __init__(self, words, size):
        self.start_time = timer()

        self.clues = words
        words = [word for word in words if len(word) <= size]

        self.ctx = z3.Context()

        # set up the set of characters that can be in the puzzle
        letters_in_puzzle = set("".join(words))
        letter, self.letters = z3.EnumSort("letter", list(letters_in_puzzle) + [BLANK], self.ctx)
        self.blank = self.letters[-1]
        self.letters = {l: self.letters[i] for i, l in enumerate(letters_in_puzzle)}
        self.letters[BLANK] = self.blank

        # set up the set of possible table positions
        self.size = size
        self.table = [[z3.Const(f"table_{x}_{y}", letter) for y in range(size)] for x in range(size)]
        self.off = z3.Const("off", letter)
              
        # set up all the variables for the words        
        self.words = {word: [[[z3.Bool(f'{word}_{x}_{y}_{o}', self.ctx) if self.fits(x, y, o, word) else z3.BoolVal(False, self.ctx)
                               for o in [ACROSS, DOWN]]
                              for y in range(size)]
                             for x in range(size)]
                      for word in words}

        # solution is the model that we will find
        self.solution = None
    
    def fits(self, i, j, orientation, word):
        if orientation == ACROSS:
            return j + len(word) <= self.size
        else:
            return i + len(word) <= self.size
        
    def get(self, i, j):
        if i < 0 or i >= self.size or j < 0 or j >= self.size:
            return self.off
        return self.table[i][j]

    def right(self, i, j):
        return self.get(i, j+1) 
    
    def left(self, i, j):
        return self.get(i, j-1) 
    
    def down(self, i, j):
        return self.get(i+1, j)
    
    def up(self, i, j):
        return self.get(i-1, j)
    
    def next(self, i, j, orientation, k):
        """Get the kth next letter in the given orientation"""
        if orientation == ACROSS:
            return self.get(i, j+k)
        else:
            return self.get(i+k, j)
        
    def prev(self, i, j, orientation, k):
        """Get the kth previous letter in the given orientation"""
        if orientation == ACROSS:
            return self.get(i, j-k)
        else:
            return self.get(i-k, j)
    
    @print_time("Position constraints")
    def position_constraints(self):
        """
        Returns a list of constraints that ensure that if a word is selected, 
        then the table is filled in correctly at the appropriate position and orientation
        """
        constraints = []
        for word, placements in self.words.items():
            for i in range(self.size):
                for j in range(self.size):
                    for o in [ACROSS, DOWN]:
                        # if the word is placed at this position and orientation, then the table must be filled in correctly
                        effect = self.prev(i, j, o, 1) == self.blank
                        for k, c in enumerate(word):
                            effect = z3.And(effect, self.next(i, j, o, k) == self.letters[c], self.ctx)
                        effect = z3.And(effect, self.next(i, j, o, len(word)) == self.blank, self.ctx)
                        constraints.append(z3.Implies(placements[i][j][o], effect, self.ctx))

            # at-most-one placement is used per word
            at_most_one = z3.AtMost(*[placements[i][j][o] for i in range(self.size) for j in range(self.size) for o in [ACROSS, DOWN]], 1)
            constraints.append(at_most_one)
        
        return constraints
    
    @print_time("Checked constraints")
    def checked_constraints(self):
        """A character is checked if it belongs to a vertical and a horizontal word. 
        All characters must be checked. This also prevents islands (single floating characters)."""
        constraints = []
        for i in range(self.size):
            for j in range(self.size):
                hcond = z3.Or(self.left(i, j) != self.blank, self.right(i, j) != self.blank, self.ctx)
                vcond = z3.Or(self.up(i, j) != self.blank, self.down(i, j) != self.blank, self.ctx)
                constraints.append(z3.Implies(self.get(i, j) != self.blank, z3.And(hcond, vcond, self.ctx), self.ctx))
        return constraints

    @print_time("Off table constraints")
    def off_table_constraints(self):
        """The table is blank off the table"""
        return [self.off == self.blank]
    
    @print_time("Word start constraints")
    def word_start_constraints(self):
        """Any time we see a start of a word (blank, letter, letter), it must be the start of a word"""
        constraints = []
        for i in range(self.size):
            for j in range(self.size):
                for o in [ACROSS, DOWN]:
                    is_start = self.prev(i, j, o, 1) == self.blank
                    is_start = z3.And(is_start, self.get(i, j) != self.blank, self.ctx)
                    is_start = z3.And(is_start, self.next(i, j, o, 1) != self.blank, self.ctx)
                    # possible word starts
                    possible = [self.words[word][i][j][o] for word in self.words]
                    constraints.append(z3.Implies(is_start,  z3.Or(*possible, self.ctx), self.ctx))

        return constraints
    
    @print_time("Symmetry constraints")
    def symmetry_constraints(self):
        """The puzzle should be rotationally symmetric"""
        constraints = []
        for i in range(self.size):
            for j in range(self.size):
                constraints.append((self.get(i, j) == self.blank) == (self.get(self.size-1-i, self.size-1-j) == self.blank))
        return constraints
    
    def get_clue(self, word):
        if word in self.clues:
            return self.clues[word]
        return ""

    def build(self, key_words = [], prompt=None, max_blanks = -1, timeout = 60):
        """
        Generates a crossword puzzle with the given words and size, optimizing for the fewest blanks
        """
        # will essentially filter out words that are too long
        key_words = [word for word in key_words if word in self.words]

        s = z3.Solver(ctx = self.ctx)
        # set a timeout
        s.set("timeout", timeout * 1000)

        s.add(self.position_constraints() + self.off_table_constraints() + self.checked_constraints() + self.word_start_constraints() + self.symmetry_constraints())
        
        key_word_placements = []
        for word in key_words:
            placements = self.words[word]
            key_word_placements += [placements[i][j][o] for i in range(self.size) for j in range(self.size) for o in [ACROSS, DOWN]]

        @print_time("Solving")
        def solve(msg):
            print(msg, end="... ", flush=True)
            result = s.check()
            if result == z3.sat:
                print("yes", end="... ")
                return s.model()
            else:
                print("not", end="... ")
            return None

        number_of_blanks = [max_blanks]
        if max_blanks < 0:
            number_of_blanks = list(range(self.size*self.size + 1))
        number_of_key_words = list(range(len(key_words) + 1))

        # create the product of the number of blanks and the number of key words
        search_space = [(k, b) for k in number_of_key_words for b in number_of_blanks]
        # we want the most key words and the least blanks
        search_space.sort(key=lambda x: (x[0], -x[1]), reverse=True)

        lower_index = 0
        upper_index = len(search_space) - 1
        mid_index = len(search_space) // 2

        while lower_index < upper_index:
            s.push()
            mid_key_words = search_space[mid_index][0]
            mid_blanks = search_space[mid_index][1]
            s.add(z3.AtMost(*[self.get(i, j) == self.blank for i in range(self.size) for j in range(self.size)], mid_blanks))
            s.add(z3.AtLeast(*key_word_placements, mid_key_words))
            model = solve(f"with at least {mid_key_words} theme words and at most {mid_blanks} blanks")
            if model is not None:
                self.solution = model
                upper_index = mid_index
                mid_index = (lower_index + upper_index) // 2
            else:
                lower_index = mid_index + 1
                mid_index = (lower_index + upper_index) // 2
            s.pop()
        print()

        assert self.solution is not None, "No solution found"

        grid = [[self.eval(self.table[x][y]) for y in range(self.size)] for x in range(self.size)]
        across = [(word, i, j, self.get_clue(word)) for word, placements in self.words.items() for i in range(self.size) for j in range(self.size) if self.eval(placements[i][j][ACROSS])]
        down = [(word, i, j, self.get_clue(word)) for word, placements in self.words.items() for i in range(self.size) for j in range(self.size) if self.eval(placements[i][j][DOWN])]

        return Crossword(grid, across, down, prompt=prompt, time=timer() - self.start_time)

    def eval(self, x):
        """Evaluates solver expression x in the context of the solution we found"""
        out = str(self.solution.evaluate(x, model_completion=True))
        if out == "True":
            return True
        elif out == "False":
            return False
        return out
