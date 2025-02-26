# Code started with https://bohlender.pro/blog/generating-crosswords-with-sat-smt/ but has changed a lot since then

import os
import z3
import csv
import json
import typer
import random

from yattag import Doc
from itertools import combinations
from timeit import default_timer as timer

from pydantic import BaseModel
from openai import OpenAI

# Input is a text desciprtion of the theme, output is a dictionary of words and clues
if os.environ["OPENAI_API_KEY"]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
else:
    raise ValueError("No OPENAI_API_KEY")

class Clue(BaseModel):
    clue: str

class WordAndClue(BaseModel):
    word: str
    clue: str

class Theme(BaseModel):
    words: list[WordAndClue]

# Decorator for tracking progress and runtime
def print_time(msg):
    def decorator(f):
        def wrapper(*args, **kwargs):
            print(f'{msg} ... ', end='', flush=True)
            start = timer()
            res = f(*args, **kwargs)
            print('{:.2f}s'.format(timer() - start))
            return res
        return wrapper
    return decorator

def cache_call(filename):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with open(filename, "r+") as f:
                cache = csv.reader(f, delimiter=";")
                # find the row with the inputs
                for row in cache:
                    if list(map(str, row[:-1])) == list(map(str, args)):
                        print(f"\n\nCache hit!!\n\n")
                        f.close()
                        return eval(row[-1])
                res = func(*args, **kwargs)
                cache = csv.writer(f, delimiter=";")
                cache.writerow(list(args) + [res])
            return res
        return wrapper
    return decorator

ACROSS = 0
DOWN = 1

class Crossword:
    @print_time("Setup")
    def __init__(self, words, size):
        words = [word for word in words if len(word) <= size]

        self.ctx = z3.Context()

        # set up the set of characters that can be in the puzzle
        letters_in_puzzle = set("".join(words))
        letter, self.letters = z3.EnumSort("letter", list(letters_in_puzzle) + ["BLANK"], self.ctx)
        self.blank = self.letters[-1]
        self.letters = {l: self.letters[i] for i, l in enumerate(letters_in_puzzle)}
        self.letters["BLANK"] = self.blank

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
    
    @print_time("Island constraints")
    def island_constraints(self):
        """There should be no single character islands"""
        constraints = []
        for i in range(self.size):
            for j in range(self.size):
                neighbors = [self.left(i, j), self.right(i, j), self.up(i, j), self.down(i, j)]
                constraints.append(z3.Implies(self.get(i, j) != self.blank, z3.Or(*[n != self.blank for n in neighbors], self.ctx), self.ctx))
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
                    constraints.append(is_start == z3.Or(*possible, self.ctx))

        return constraints
    
    @print_time("Symmetry constraints")
    def symmetry_constraints(self):
        """The puzzle should be rotationally symmetric"""
        constraints = []
        for i in range(self.size):
            for j in range(self.size):
                constraints.append((self.get(i, j) == self.blank) == (self.get(self.size-1-i, self.size-1-j) == self.blank))
        return constraints
    
    def generate(self, theme = [], max_blanks = -1, timeout = 60):
        """
        Generates a crossword puzzle with the given words and size, optimizing for the fewest blanks
        """
        s = z3.Solver(ctx = self.ctx)
        # set a timeout
        s.set("timeout", timeout * 1000)

        s.add(self.position_constraints() + self.off_table_constraints() + self.island_constraints() + self.word_start_constraints() + self.symmetry_constraints())

        for word in theme:
            assert word in self.words, f"Word {word} not in word list {self.words.keys()}"
            placements = self.words[word]
            condition = z3.Or(*[placements[i][j][o] for i in range(self.size) for j in range(self.size) for o in [ACROSS]], self.ctx)
            s.add(condition)

        if (max_blanks > 0):
            print(f"Solving with at most {max_blanks} blanks ({100*max_blanks//(self.size*self.size)}% of table) ...", end=' ', flush=True)
            time_before = timer()
            s.add(z3.AtMost(*[self.get(i, j) == self.blank for i in range(self.size) for j in range(self.size)], max_blanks))
            result = s.check()
            print('{:.2f}s'.format(timer() - time_before))
            if result == z3.sat:
                print("  - succeeded")
                self.solution = s.model()
            else:
                print("  - failed")
        else:
            lower = 0
            upper = self.size*self.size + 1
            mid = (lower + upper) // 2

            while lower < upper:
                print(f"Solving with at most {mid} blanks ({100*mid//(self.size*self.size)}% of table) ...", end=' ', flush=True)
                time_before = timer()

                s.push()
                s.add(z3.AtMost(*[self.get(i, j) == self.blank for i in range(self.size) for j in range(self.size)], mid))

                result = s.check()
                print('{:.2f}s'.format(timer() - time_before))

                if result == z3.sat:
                    print("  - succeeded")
                    self.solution = s.model()
                    upper = mid
                    mid = (lower + upper) // 2
                else:
                    print("  - failed")
                    s.pop()
                    lower = mid + 1
                    mid = (lower + upper) // 2
            print()

        assert self.solution is not None, "No solution found"

    def eval(self, x):
        """Evaluates solver expression x in the context of the solution we found"""
        out = str(self.solution.evaluate(x, model_completion=True))
        if out == "True":
            return True
        elif out == "False":
            return False
        return out

    def print_crossword(self, clues):
        for i in range(self.size):
            for j in range(self.size):
                char = self.eval(self.table[i][j])
                if char == "BLANK":
                    print("*", end=" ")
                else:
                    print(char, end=" ")
            print()
        print()

    def to_json(self, clues):
        output = {}
        output["size"] = self.size
        output["table"] = [[self.eval(self.get(i, j)) for j in range(self.size)] for i in range(self.size)]
        # get all the placements
        across = []
        down = []
        for word, placements in self.words.items():
            word = word.upper()
            for i in range(self.size):
                for j in range(self.size):
                    for o in [ACROSS, DOWN]:
                        if self.eval(placements[i][j][o]):
                            if o == ACROSS:
                                across.append({"word": word, "clue": clues[word], "row": i, "col": j})
                            else:
                                down.append({"word": word, "clue": clues[word], "row": i, "col": j})

        output["words"] = {"across": across, "down": down}
        return output

@cache_call(".theme-calls.csv")
@print_time("Generating theme words and clues with an LLM")
def llm_generate_theme(theme, size):    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are Will Shortz, the crossword puzzle editor for The New York Times, and you are excited to help me make a great crossword. "},
            {"role": "user", "content": f"Provide {size} words and clues for a crossword puzzle with the theme \"{theme}\"."},
        ],
        response_format=Theme,
    )

    event = completion.choices[0].message.parsed
    words_x_clues = {}
    for e in event.words:
        word = e.word.upper()
        if word not in words_x_clues and len(word) <= size:
            words_x_clues[word] = e.clue
    return words_x_clues

@cache_call(".clue-calls.csv")
@print_time("Generating a clue with an LLM")
def llm_generate_clue(word, theme):
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are Will Shortz, the crossword puzzle editor for The New York Times, and you are excited to help me make a great crossword. "},
            {"role": "user", "content": f"Provide a clue for the word \"{word}\". Use the theme \"{theme}\", if you can."},
        ],
        response_format=Clue,
    )

    event = completion.choices[0].message.parsed
    return event.clue

# Helpers and main functions

def read_theme(csv_file):
    words_x_clues = {}
    with open(csv_file, "r") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            words_x_clues[row[0].upper()] = row[1]
    return words_x_clues


def read_bank(txt_file, min_score, max_length):
    words_x_clues = {}
    with open(txt_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            # split the line into word;score
            word, score = line.strip().split(";")
            if int(score) >= min_score and len(word) <= max_length:
                words_x_clues[word.upper()] = ""
    return words_x_clues

def json_to_html_table(json, cell_to_number):
    doc, tag, text = Doc().tagtext()
    with tag("table", id="grid"):
        for i in range(len(json["table"])):
            row = json["table"][i]
            with tag("tr"):
                for j in range(len(row)):
                    cell = row[j].upper()
                    if cell == "BLANK":
                        with tag("td", klass="blank"):
                            text(" ")
                    else:
                        with tag("td", klass="todo"):
                            number = cell_to_number(i, j)
                            number = "" if number < 1 else number
                            with tag("div", klass="number", data_number=number):
                                text(number)
                            with tag("input", type="text", id=f"{i}_{j}", name=cell, max_length=1, min_length=1):
                                text(" ")
    return doc.getvalue()

def json_to_html(json, cell_to_number):
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html", lang="en"):
        with tag("head"):
            doc.stag("meta", charset="UTF-8")
            doc.stag("meta", name="viewport", content="width=device-width, initial-scale=1.0")
            doc.asis("<title>María's Crossword</title>")
            doc.stag("link", rel="stylesheet", href="crossword.css")
            doc.asis("<script src=\"crossword.js\"></script>")
        with tag("body"):
            doc.asis(json_to_html_table(json, cell_to_number))

            across = [(cell_to_number(word["row"], word["col"]), word["clue"]) for word in json["words"]["across"]]
            across.sort(key=lambda x: x[0])
            down = [(cell_to_number(word["row"], word["col"]), word["clue"]) for word in json["words"]["down"]]
            down.sort(key=lambda x: x[0])

            with tag("div", id="clues"):
                if across:
                    with tag("h2"):
                        text("Across")
                    with tag("ul", id="across"):
                        for (num, clue) in across:
                            with tag("li", data_number=num):
                                text(f"{num}. {clue}")
                if down:
                    with tag("h2"):
                        text("Down")
                    with tag("ul", id="down"):
                        for (num, clue) in down:
                            with tag("li", data_number=num):
                                text(f"{num}. {clue}")
        
        with tag("footer"):
            if "prompt" in json:
                with tag("div", id="prompt"):
                    text(f"Prompt: \"{json['prompt']}\"")
            if "time" in json:
                with tag("div", id="time"):
                    text(f"Time: {json['time']:.2f} seconds")

    return doc.getvalue()

def pick_random_subset(words_x_clues, sample_size):
    filtered = words_x_clues
    selected = random.sample(list(filtered.keys()), sample_size)
    filtered = {k: filtered[k] for k in selected}
    return filtered

def load_bank(file, score, sample, max_length = 5):
    # non-theme words have to be 5 letters or less
    if file.endswith(".txt"):
        combined = pick_random_subset(read_bank(file, score, max_length), sample)
    else:
        combined = pick_random_subset(read_theme(file), sample)
    return combined

def generate_cell_to_number(json):
    numbers = list(set([(word["row"], word["col"]) for word in json["words"]["across"] + json["words"]["down"]]))
    numbers.sort()

    def cell_to_number(row, col):
        for index in range(len(numbers)):
            if numbers[index] == (row, col):
                return index + 1
        return -1
    
    return cell_to_number

def generate_json(theme, combined, size, max_blanks, timeout):
    c = Crossword(combined.keys(), size)
    c.generate(theme, max_blanks, timeout)

    c.print_crossword(combined)
    json = c.to_json(combined)

    return json, generate_cell_to_number(json)


def complete_clues(json, theme, theme_words_x_clues, manual):
    for word in json["words"]["across"] + json["words"]["down"]:
        if word["word"] in theme_words_x_clues:
            word["clue"] = theme_words_x_clues[word["word"]]
        elif manual:
            clue = input(f"Provide a clue for the word \"{word['word']}\": ")
            word["clue"] = clue
        else:
            word["clue"] = llm_generate_clue(word["word"], theme)
    return json

app = typer.Typer(pretty_exceptions_enable=False, add_completion=False, help="Generate a crossword puzzle")

@app.command(short_help="Generate a crossword puzzle from words and clues")
def manual(
    theme: str = typer.Argument(..., help="Path to csv file containing required words and clues"),
    bank: str = typer.Option(..., help="Path to a txt file containing a bank of optional words (crossword compiler format)"),
    sample: int = typer.Option(500, help="Number of bank words to sample"),
    score: int = typer.Option(50, help="Minimum score for bank words"),
    size: int = typer.Option(-1, help="Size of the crossword puzzle"),
    max_blanks: int = typer.Option(-1, help="Maximum number of blanks allowed in the puzzle"),
    timeout: int = typer.Option(60, help="Timeout for the solver in seconds"),
    output: str = typer.Option("index.html", help="Output file (.html or .json)"),
):
    assert output.endswith(".html") or output.endswith(".json"), "output file must be .html or .json"
    assert bank == None or bank.endswith(".txt"), "bank file must be txt file"
    
    theme_words_x_clues = read_theme(theme)
    
    if size == -1:
        size = max([len(word) for word in theme_words_x_clues])
    else:
        for word in theme_words_x_clues:
            assert len(word) <= size, f"Word {word} is too long for the crossword size {size}"

    assert size > 0, "size must be greater than 0"

    combined = load_bank(bank, score, sample)
    combined.update(theme_words_x_clues)

    out, cell_to_number = generate_json(theme_words_x_clues.keys(), combined, size, max_blanks, timeout)

    theme = " ".join([f"{word}: {clue}" for word, clue in theme_words_x_clues.items()])
    out = complete_clues(out, theme, theme_words_x_clues, True)

    with open(output, "w") as f:
        # if output ends in .html, write html, otherwise write json
        if output.endswith(".html"):
            f.write(json_to_html(out, cell_to_number))
        else:
            json.dump(out, f)

@app.command(short_help="Generate a crossword puzzle from a theme description")
def auto(
    theme: str = typer.Argument(..., help="Description of the puzzle theme"),
    bank: str = typer.Option(..., help="Path to a txt file containing a bank of optional words (crossword compiler format)"),
    sample: int = typer.Option(500, help="Number of bank words to sample"),
    score: int = typer.Option(50, help="Minimum score for bank words"),
    size: int = typer.Option(..., help="Size of the crossword puzzle"),
    max_blanks: int = typer.Option(-1, help="Maximum number of blanks allowed in the puzzle"),
    timeout: int = typer.Option(60, help="Timeout for the solver in seconds"),
    output: str = typer.Option("index.html", help="Output file (.html or .json)"),
):
    start_time = timer()

    assert output.endswith(".html") or output.endswith(".json"), "output file must be .html or .json"
    assert bank.endswith(".txt"), "bank file must be txt file"
    assert size > 0, "size must be greater than 0"

    theme_words_x_clues = llm_generate_theme(theme, size)

    # try every combination of theme words without bank words, from largest to smallest, until one works
    picked = None
    power_set = []
    for i in range(3, min(len(theme_words_x_clues), (size // 2) + 1)):
        power_set += combinations(theme_words_x_clues.keys(), i)
    # sort the power set in a random order
    random.shuffle(power_set)
    for attempt in power_set:
        print(f"\nTrying theme {attempt}")
        combined = load_bank(bank, score, 0)
        combined.update({k: theme_words_x_clues[k] for k in attempt})
        try:
            generate_json(attempt, combined, size, -1, 20)
            print(f"Found one!")
            picked = attempt
            break
        except AssertionError as e:
            print(f"Assertion failed: {e}")
            continue

    if picked is None:
        print("Failed to generate a crossword puzzle")
        return

    print(f"Generating crossword with theme {picked}")
    combined = load_bank(bank, score, sample)
    combined.update({k: theme_words_x_clues[k] for k in picked})
    out, cell_to_number = generate_json(picked, combined, size, max_blanks, timeout)

    out = complete_clues(out, theme, theme_words_x_clues, False)

    # add the theme to the output
    out["prompt"] = theme
    out["time"] = timer() - start_time

    with open(output, "w") as f:
        # if output ends in .html, write html, otherwise write json
        if output.endswith(".html"):
            f.write(json_to_html(out, cell_to_number))
        else:
            json.dump(out, f)

@app.command(short_help="Convert a json file to html")
def web(
    input: str = typer.Argument(..., help="Path to json file to convert"),
    output: str = typer.Option("index.html", help="Output file (.html)"),
):
    assert input.endswith(".json"), "input file must be .json"
    assert output.endswith(".html"), "output file must be .html"

    with open(input, "r") as f:
        out = json.load(f)

    with open(output, "w") as f:
        f.write(json_to_html(out, generate_cell_to_number(out)))

if __name__ == "__main__":
    app()