import json

from crossword.constants import BLANK
from crossword.crossword import Crossword

def parse_markdown(markdown, check=True):
    """
    Parse a markdown string into a crossword grid. For example,
    
    ---
    size: "5"
    time: "0.36 seconds"
    ---
    # Crossword
    ## Grid
    | | | | | |
    |-|-|-|-|-|
    |*|*|R|H|O|
    |*|R|E|I|N|
    |A|I|S|L|E|
    |N|O|E|L|*|
    |I|T|T|*|*|

    ## Clues
    ### Across
    (0, 2): Greek "r"
    (1, 1): Free ___ (total control)
    (2, 0): Choice plane seating
    (3, 0): Yule tune
    (4, 0): Cousin ___ (Addams Family member)

    ### Down
    (0, 2): Bowling alley button
    (0, 3): What Jack and Jill went up
    (0, 4): Word repeated in "It takes ___ to know ___"
    (1, 1): Uproar
    (2, 0): Alex and ___ (jewelry retailer)
    
    into a Crossword object.
    """
    lines = markdown.strip().split("\n")
    grid = []
    across = []
    down = []
    mode = None
    for line in lines:
        if line.startswith("# "):
            mode = "grid"
        elif line.startswith("## Clues"):
            mode = "clues"
            # Remove the header row from the grid and the last row
            grid = grid[3:-1]
        elif line.startswith("### Across"):
            mode = "across"
        elif line.startswith("### Down"):
            mode = "down"
        elif mode == "grid":
            grid.append([BLANK if char == "*" else char for char in line.split("|")[1:-1]])
        elif mode == "down":
            parts = line.split(":")
            if len(parts) == 2:
                row = int(parts[0].strip()[1:-1].split(",")[0])
                col = int(parts[0].strip()[1:-1].split(",")[1])
                clue = parts[1].strip()
                # find the word in the grid
                word = find_word(grid, row, col, "down")
                down.append((word, row, col, clue))
        elif mode == "across":
            parts = line.split(":")
            if len(parts) == 2:
                row = int(parts[0].strip()[1:-1].split(",")[0])
                col = int(parts[0].strip()[1:-1].split(",")[1])
                clue = parts[1].strip()
                # find the word in the grid
                word = find_word(grid, row, col, "across")
                across.append((word, row, col, clue))

    # Create a Crossword object and return it
    return Crossword(grid, across, down, check=check)


def find_word(grid, row, col, direction):
    """
    Find the word in the grid starting from (row, col) in the given direction.
    """
    word = ""
    if direction == "across":
        for j in range(col, len(grid[row])):
            if grid[row][j] == BLANK:
                break
            word += grid[row][j]
    elif direction == "down":
        for i in range(row, len(grid)):
            if grid[i][col] == BLANK:
                break
            word += grid[i][col]
    return word


def parse_json(json_string, check=True):
    """
    Parse a json string like 

    {
        "size": 5,
        "table": [
            [
                "BLANK",
                "BLANK",
                "R",
                "H",
                "O"
            ],
            [
                "BLANK",
                "R",
                "E",
                "I",
                "N"
            ],
            [
                "A",
                "I",
                "S",
                "L",
                "E"
            ],
            [
                "N",
                "O",
                "E",
                "L",
                "BLANK"
            ],
            [
                "I",
                "T",
                "T",
                "BLANK",
                "BLANK"
            ]
        ],
        "words": {
            "across": [
                {
                    "word": "RHO",
                    "row": 0,
                    "col": 2,
                    "clue": "Greek \"r\""
                },
                {
                    "word": "REIN",
                    "row": 1,
                    "col": 1,
                    "clue": "Free ___ (total control)"
                },
                {
                    "word": "AISLE",
                    "row": 2,
                    "col": 0,
                    "clue": "Choice plane seating"
                },
                {
                    "word": "NOEL",
                    "row": 3,
                    "col": 0,
                    "clue": "Yule tune"
                },
                {
                    "word": "ITT",
                    "row": 4,
                    "col": 0,
                    "clue": "Cousin ___ (Addams Family member)"
                }
            ],
            "down": [
                {
                    "word": "ANI",
                    "row": 2,
                    "col": 0,
                    "clue": "Alex and ___ (jewelry retailer)"
                },
                {
                    "word": "RIOT",
                    "row": 1,
                    "col": 1,
                    "clue": "Uproar"
                },
                {
                    "word": "RESET",
                    "row": 0,
                    "col": 2,
                    "clue": "Bowling alley button"
                },
                {
                    "word": "HILL",
                    "row": 0,
                    "col": 3,
                    "clue": "What Jack and Jill went up"
                },
                {
                    "word": "ONE",
                    "row": 0,
                    "col": 4,
                    "clue": "Word repeated in \"It takes ___ to know ___\""
                }
            ]
        },
        "time": 0.34075580805074424
    }

    into a Crossword object.
    """
    data = json.loads(json_string)
    grid = data["table"]
    across = []
    down = []
    for word in data["words"]["across"]:
        across.append((word["word"], word["row"], word["col"], word["clue"]))
    for word in data["words"]["down"]:
        down.append((word["word"], word["row"], word["col"], word["clue"]))
    time = data.get("time", None)
    prompt = data.get("prompt", None)
    # Convert BLANK to the BLANK constant
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if grid[i][j] == "BLANK":
                grid[i][j] = BLANK
    return Crossword(grid, across, down, time=time, prompt=prompt, check=check)