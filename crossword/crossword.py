from crossword.constants import BLANK
from yattag import Doc

class Crossword:
    def __init__(self, grid, across, down, prompt=None, time=None, check=True):
        self.grid = grid # 2D array of letters and BLANK
        assert len(grid) == len(grid[0])
        self.size = len(grid)
        
        self.across = across # [(word, row, col, clue)]
        self.down = down # [(word, row, col, clue]

        # optional fields for printing 
        self.prompt = prompt
        self.time = time

        print(self)

        if check:
            self.check_position_constraints()
            self.check_checked_constraints()
            self.check_symmetry_constraints()

    def cell_to_number(self, row, col):
        # get all the rows and columns of the words
        words = list(set([(x, y) for (_, x, y, _) in self.across] + [(x, y) for (_, x, y, _) in self.down]))
        words.sort()
        for i in range(len(words)):
            if words[i] == (row, col):
                return i + 1
        return -1

    def check_position_constraints(self):
        """
        If a word is selected, it must be placed in the grid.
        """
        checklist = set()
        for position in self.across:
            word, row, col, _ = position
            for i in range(len(word)):
                checklist.add((row, col + i))
                assert self.grid[row][col + i] == word[i], f"Word {word} is not placed correctly at ({row}, {col})"
        for position in self.down:
            word, row, col, _ = position
            for i in range(len(word)):
                checklist.add((row + i, col))
                assert self.grid[row + i][col] == word[i], f"Word {word} is not placed correctly at ({row}, {col})"
        
        # every position that has not been added to the checklist must be blank
        for i in range(self.size):
            for j in range(self.size):
                if (i, j) not in checklist:
                    assert self.grid[i][j] == BLANK, f"Position ({i}, {j}) is not blank" 

    def check_checked_constraints(self):
        """
        Every letter belongs to an across and a down word.
        """
        for i in range(self.size):
            for j in range(self.size):
                if self.grid[i][j] != BLANK:
                    left_neighbor = self.grid[i][j-1] if j > 0 else BLANK
                    right_neighbor = self.grid[i][j+1] if j < self.size - 1 else BLANK
                    up_neighbor = self.grid[i-1][j] if i > 0 else BLANK
                    down_neighbor = self.grid[i+1][j] if i < self.size - 1 else BLANK
                    assert (left_neighbor != BLANK or right_neighbor != BLANK), f"Letter {self.grid[i][j]} at ({i}, {j}) is not part of an across word"
                    assert (up_neighbor != BLANK or down_neighbor != BLANK), f"Letter {self.grid[i][j]} at ({i}, {j}) is not part of a down word"

    def check_symmetry_constraints(self):
        """
        The crossword is symmetric in terms of the BLANKs
        """
        for i in range(self.size):
            for j in range(self.size):
                assert (self.grid[i][j] == BLANK) == (self.grid[self.size - i - 1][self.size - j - 1] == BLANK), f"Grid is not symmetric at ({i}, {j})"

    def to_json(self):
        output = {}
        output["size"] = self.size
        output["table"] = self.grid
        across = [{"word": word, "row": row, "col": col, "clue": clue} for (word, row, col, clue) in self.across]
        down = [{"word": word, "row": row, "col": col, "clue": clue} for (word, row, col, clue) in self.down]
        output["words"] = {"across": across, "down": down}
        if self.prompt:
            output["prompt"] = self.prompt
        if self.time:
            output["time"] = self.time
        return output

    def _to_html_table(self):
        doc, tag, text = Doc().tagtext()
        with tag("table", id="grid"):
            for i in range(len(self.grid)):
                row = self.grid[i]
                with tag("tr"):
                    for j in range(len(row)):
                        cell = row[j].upper()
                        if cell == "BLANK":
                            with tag("td", klass="blank"):
                                text(" ")
                        else:
                            with tag("td", klass="todo"):
                                number = self.cell_to_number(i, j)
                                number = "" if number < 1 else number
                                with tag("div", klass="number", data_number=number):
                                    text(number)
                                with tag("input", type="text", id=f"{i}_{j}", name=cell, maxlength=1, minlength=1):
                                    text(" ")
        return doc.getvalue()

    def to_html(self):
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
                doc.asis(self._to_html_table())
                across = [(self.cell_to_number(row, col), clue) for _, row, col, clue in self.across]
                across.sort(key=lambda x: x[0])
                down = [(self.cell_to_number(row, col), clue) for _, row, col, clue in self.down]
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
            
            if self.prompt or self.time:
                with tag("footer"):
                    if self.prompt:
                        with tag("div", id="prompt"):
                            text(f"Prompt: \"{self.prompt}\"")
                    if self.time:
                        with tag("div", id="time"):
                            text(f"Time: {self.time:.2f} seconds")

        return doc.getvalue()
    
    def to_markdown(self):
        out = "---\n"
        out += f"size: \"{self.size}\"\n"
        if self.prompt:
            out += f"prompt: \"{self.prompt}\"\n"
        if self.time:
            out += f"time: \"{self.time:.2f} seconds\"\n"
        out += "---\n"
        out += "# Crossword\n"
        out += "## Grid\n"
        out += "|"
        for _ in range(self.size):
            out += " |"
        out += "\n"
        out += "|"
        for _ in range(self.size):
            out += "-|"
        out += "\n"
        for i in range(self.size):
            out += "|"
            for j in range(self.size):
                char = self.grid[i][j].upper()
                if char == BLANK:
                    out += "*|"
                else:
                    out += char + "|"
            out += "\n"
        out += "\n"
        out += "## Clues\n"

        across = [(self.cell_to_number(row, col), row, col, clue) for _, row, col, clue in self.across]
        across.sort(key=lambda x: x[0])
        down = [(self.cell_to_number(row, col), row, col, clue) for _, row, col, clue in self.down]
        down.sort(key=lambda x: x[0])

        out += "### Across\n"
        for (_, row, col, clue) in across:
            out += f"({row}, {col}): {clue}\n"
        out += "\n"
        out += "### Down\n"
        for (_, row, col, clue) in down:
            out += f"({row}, {col}): {clue}\n"
        out += "\n"
        return out
    
    __str__ = to_markdown