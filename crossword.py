# Code adapted from https://bohlender.pro/blog/generating-crosswords-with-sat-smt/
# All credit goes to the original author. I have made some modifications to the code to fit my needs.


from collections import namedtuple
from itertools import *
from timeit import default_timer as timer

from z3 import *  # Provided by `pip install z3-solver==`4.11.2.0`


# Decorator for tracking progress and runtime
def print_time(msg):
    def decorator(f):
        def wrapper(*args, **kwargs):
            print(f'{msg} ... ', end='')
            start = timer()
            res = f(*args, **kwargs)
            print('{:.2f}s'.format(timer() - start))
            return res

        return wrapper

    return decorator


Placement = namedtuple('Placement', ['x', 'y', 'horizontal'])


def generateCrossword(words, size, minQuality):
    # Input validation
    assert minQuality >= 0

    # Encode valid word placements (over some set of placement variables)
    constraints, placement_vars = encodeProblem(words, size, minQuality)

    # Solve SMT instance & pretty-print result (if one exists)
    model = solve(constraints)
    if model:
        placement = interpret(model, placement_vars)
        print("Constraints satisfiable")
        return placement
    else:
        print("Constraints unsatisfiable")
        return None


@print_time("Encoding")
def encodeProblem(words, size, minQuality):
    # Variables encoding the placement of each word, i.e. setting
    # `placement_vars['doom'][0][3][1]` to `True` denotes
    # 'doom' being placed vertically at (x=3, y=0)
    placement_vars = {word: [[[Bool(f'{word}_{x},{y}_{orientation}')
                               for orientation in ['horizontal', 'vertical']]
                              for x in range(size)]
                             for y in range(size)]
                      for word in words}

    # Variables encoding the subset of words actually put on the grid
    word_selection = {word: Bool(f'{word}_selected') for word in words}

    # Constants representing the words' characters (and "no character")
    chars = list(set("".join(words)))
    char_sort, char_constants = EnumSort(f'Chars{minQuality}', chars + ['empty'])
    char_empty = char_constants[-1]
    chars_enc = {c: sym for c, sym in zip(chars, char_constants)}

    # Variables encoding the character in each grid cell
    grid = [[Const(f'grid_{x}_{y}', char_sort) for x in range(size)]
            for y in range(size)]

    # `possible_placements[y][x][0]` will contain the placement variables
    # of all words what can be placed horizontally at coord (x,y)
    possible_placements = [[[[]
                             for orientation in ['horizontal', 'vertical']]
                            for x in range(size)]
                           for y in range(size)]

    # Word placement determines characters on grid
    res = []
    for word in words:
        word_placement_vars = []
        for x, y in product(range(size), repeat=2):
            # Fits horizontally
            if x + len(word) <= size:
                # Keep track that this is a possible placement
                word_placement_vars.append(placement_vars[word][y][x][0])
                possible_placements[y][x][0].append(placement_vars[word][y][x][0])

                # Effect (of this placement) on grid
                word_symbols = grid[y][x:x + len(word)]
                match_expr = And([chars_enc[c] == sym for c, sym in zip(word, word_symbols)])
                res.append(Implies(placement_vars[word][y][x][0], match_expr))

                # Word must be bounded by spaces (or grid borders)
                bounding_chars = []
                if x - 1 >= 0:
                    bounding_chars.append(grid[y][x - 1])
                if x + len(word) < size:
                    bounding_chars.append(grid[y][x + len(word)])
                bounded_by_spaces = And([sym == char_empty for sym in bounding_chars])
                res.append(Implies(placement_vars[word][y][x][0], bounded_by_spaces))

            # Fits vertically (analogous to the above case)
            if y + len(word) <= size:
                # Keep track that this is a possible placement
                word_placement_vars.append(placement_vars[word][y][x][1])
                possible_placements[y][x][1].append(placement_vars[word][y][x][1])

                # Effect (of this placement) on grid
                word_symbols = [grid[y + i][x] for i in range(len(word))]
                match_expr = And([chars_enc[c] == sym for c, sym in zip(word, word_symbols)])
                res.append(Implies(placement_vars[word][y][x][1], match_expr))

                # Word must be bounded by spaces (or grid borders)
                bounding_chars = []
                if y - 1 >= 0:
                    bounding_chars.append(grid[y - 1][x])
                if y + len(word) < size:
                    bounding_chars.append(grid[y + len(word)][x])
                bounded_by_spaces = And([sym == char_empty for sym in bounding_chars])
                res.append(Implies(placement_vars[word][y][x][1], bounded_by_spaces))

        # If the word is selected, exactly one placement must be used
        res.append(AtMost(*word_placement_vars, 1))
        res.append(Implies(word_selection[word], Or(word_placement_vars)))

    # Every non-empty sequence (of length > 1) must match a word
    for x, y in product(range(size), repeat=2):
        # Start of horizontal sequence
        if x + 1 < size:
            seq_start = And(grid[y][x - 1] == char_empty if x - 1 >= 0 else True,
                            grid[y][x] != char_empty,
                            grid[y][x + 1] != char_empty)
            res.append(seq_start == Or(possible_placements[y][x][0]))

        # Start of vertical sequence (analogous to the above case)
        if y + 1 < size:
            seq_start = And(grid[y - 1][x] == char_empty if y - 1 >= 0 else True,
                            grid[y][x] != char_empty,
                            grid[y + 1][x] != char_empty)
            res.append(seq_start == Or(possible_placements[y][x][1]))

    # Require grid symbols to form a single connected component (CC)
    ccStartRow = [Bool(f'ccStart_{y}') for y in range(size)]
    ccStart = [[Bool(f'ccStart_{x},{y}') for x in range(size)]
               for y in range(size)]
    inCc = [[[Bool(f'reach{i}_{x},{y}') for i in range(maxDistance(size) + 1)]
             for x in range(size)] for y in range(size)]
    for y in range(size):
        # CC starts in row y
        notInPrevRows = And([Not(ccStartRow[i]) for i in range(y)])
        inCurRow = Or([grid[y][x] != char_empty for x in range(size)])
        res.append(And(inCurRow, notInPrevRows) == ccStartRow[y])

        for x in range(size):
            # CC starts at x,y
            notInPrevPos = And([Not(ccStart[y][i]) for i in range(x)])
            inCurPos = grid[y][x] != char_empty
            res.append(And(ccStartRow[y], inCurPos, notInPrevPos) == ccStart[y][x])

            # Only CC start position reaches itself in 0 steps
            res.append(ccStart[y][x] == inCc[y][x][0])

            # Symbol at x,y reaches CC start in `i` steps if
            # - it already reaches it in `i-1` steps, or
            # - neighbour symbol reaches it in `i-1` steps
            for i in range(1, maxDistance(size) + 1):
                reasons = [inCc[y][x][i - 1]]
                if x - 1 >= 0: reasons.append(inCc[y][x - 1][i - 1])
                if x + 1 < size: reasons.append(inCc[y][x + 1][i - 1])
                if y - 1 >= 0: reasons.append(inCc[y - 1][x][i - 1])
                if y + 1 < size: reasons.append(inCc[y + 1][x][i - 1])
                res.append(Implies(inCc[y][x][i],
                                   And(grid[y][x] != char_empty, Or(reasons))))

            # All non-empty grid entries must reach the CC start
            res.append(Implies(grid[y][x] != char_empty, inCc[y][x][maxDistance(size)]))

    # Require the solution to satisfy some quality criterion
    # Here: Quality corresponds to the sum of the selected words' lengths
    res.append(PbGe([(var, len(w)) for w, var in word_selection.items()], minQuality))

    return res, placement_vars


@print_time("Solving")
def solve(constraints):
    # Solve via quantifier-free finite domain solver
    s = SolverFor('QF_FD')
    s.add(constraints)
    # set a timeout of 120 seconds
    s.set("timeout", 120000)
    return s.model() if s.check() == sat else None


def interpret(model, placement_vars):
    placement = dict()
    for word, word_placement_vars in sorted(placement_vars.items()):
        for y in range(len(word_placement_vars)):
            for x in range(len(word_placement_vars[y])):
                if is_true(model.eval(word_placement_vars[y][x][0])):
                    placement[word] = Placement(x, y, True)
                elif is_true(model.eval(word_placement_vars[y][x][1])):
                    placement[word] = Placement(x, y, False)

    return placement


def printPlacement(placement, size):
    # Pretty print placement details
    placed_symbols = sum([len(w) for w in placement.keys()])
    print(f'Placed {len(placement)} words ({placed_symbols} symbols):')
    for i, word in enumerate(placement):
        print('{:2d}) {} {}'.format(i + 1, word, placement[word]))

    # Fill explicit grid with characters from interpretation (rest are spaces)
    grid = [[' ' for x in range(size)] for y in range(size)]
    for word, placement in placement.items():
        for i, c in enumerate(word):
            x = placement.x + i if placement.horizontal else placement.x
            y = placement.y if placement.horizontal else placement.y + i
            grid[y][x] = c

    # Pretty print grid
    print('┌' + '┬'.join('─' * size) + '┐')
    for y, row in enumerate(grid):
        if y != 0 and y != len(grid):
            print('├' + '┼'.join('─' * size) + '┤')
        print('│' + '│'.join(row) + '│')
    print('└' + '┴'.join('─' * size) + '┘')


# Max distance between placed characters (if they form a component)
def maxDistance(size):
    return (size + 1) ** 2 // 2 - 1  # Tighter bound than size**2


def wordToNumber(word, placements):
    # create a set of all the x and y coordinates of the placements
    coordinates = list(set([(p.x, p.y) for p in placements.values()]))
    # sort the coordinates
    coordinates.sort(key=lambda x: (x[1], x[0]))
    # find the index of the placement in the sorted list
    index = coordinates.index((placements[word].x, placements[word].y))
    return index + 1


def printCrossword(words_to_clues, placement, size):
    # Write an HTML table with the crossword and clues to a file
    with open("index.html", "w") as f:

        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>María's Crossword</title>
    <link rel="stylesheet" href="style.css">
    <script src="crossword.js"></script>
</head>
<body>""")

        f.write("<table id=\"grid\">\n")
        for y in range(size):
            f.write("<tr>\n")
            for x in range(size):
                number = ""
                letter = " "
                for word, p in placement.items():
                    if p.horizontal and p.y == y and p.x <= x < p.x + len(word):
                        letter = word[x - p.x]
                    elif not p.horizontal and p.x == x and p.y <= y < p.y + len(word):
                        letter = word[y - p.y]
                    if x == p.x and y == p.y:
                        counter = wordToNumber(word, placement)
                        number = f"<div class=\"number\">{counter}</div>"
                if letter == " ":
                    f.write("<td class=\"black\"></td>")
                else:
                    f.write(f"<td class=\"todo\">{number}<input type=\"text\" id=\"{x}_{y}\" name=\"{letter}\" required minlength=\"1\" maxlength=\"1\" class=\"letter\"></input></td>")
            f.write("</tr>\n")
        f.write("</table>\n")

        # get the horizontal and vertical words
        horizontal_words = [word for word, p in placement.items() if p.horizontal]
        horizontal_words.sort(key=lambda x: wordToNumber(x, placement))
        vertical_words = [word for word, p in placement.items() if not p.horizontal]
        vertical_words.sort(key=lambda x: wordToNumber(x, placement))

        # write the clues as a list
        f.write("<div id=\"clues\">\n")
        f.write("<h2>Across</h2>\n")
        f.write("<ul>\n")
        for word in horizontal_words:
            f.write(f"<li>{wordToNumber(word, placement)}. {words_to_clues[word]}</li>\n")
        f.write("</ul>\n")
        f.write("<h2>Down</h2>\n")
        f.write("<ul>\n")
        for word in vertical_words:
            f.write(f"<li>{wordToNumber(word, placement)}. {words_to_clues[word]}</li>\n")
        f.write("</ul>\n")
        f.write("</div>\n")

        f.write("</body>\n</html>")


if __name__ == '__main__':

    # load current.csv file into words_to_clues
    words_to_clues = {}
    with open("current.csv", "r") as f:
        # skip the first line
        f.readline()
        for line in f:
            word, clue = line.strip().split(";")
            words_to_clues[word.strip().lower()] = clue.strip()

    words = list(set(words_to_clues.keys()))
    size = max(len(w) for w in words)

    minimum = 50
    maximum = 200
    mid = (minimum + maximum) // 2

    placement = None

    while minimum < maximum:
        print(f"Trying quality {mid}")
        quality = mid
        tmp_placement = generateCrossword(words, size, quality)
        if tmp_placement:
            placement = tmp_placement
            minimum = mid + 1
        else:
            maximum = mid - 1
        mid = (minimum + maximum) // 2
        print()

    print(f"\nFinal quality: {mid}")
    printPlacement(placement, size)
    printCrossword(words_to_clues, placement, size)