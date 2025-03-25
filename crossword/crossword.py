from crossword.constants import BLANK
from crossword.llm import llm_generate_clue

from yattag import Doc

class Crossword:
    def __init__(self, grid, across, down, prompt=None, time=None):
        self.grid = grid # 2D array of letters and BLANK
        assert len(grid) == len(grid[0])
        self.size = len(grid)
        
        self.across = across # [(word, row, col, clue)]
        self.down = down # [(word, row, col, clue]

        # optional fields for printing 
        self.prompt = prompt
        self.time = time

    def cell_to_number(self, row, col):
        # get all the rows and columns of the words
        words = list(set([(x, y) for (_, x, y, _) in self.across] + [(x, y) for (_, x, y, _) in self.down]))
        words.sort()
        for i in range(len(words)):
            if words[i] == (row, col):
                return i + 1
        return -1

    def update_clues(self, words_to_clues):
        for i in range(len(self.across)):
            word = self.across[i][0]
            if word in words_to_clues:
                self.across[i] = (word, self.across[i][1], self.across[i][2], words_to_clues[word])
        for i in range(len(self.down)):
            word = self.down[i][0]
            if word in words_to_clues:
                self.down[i] = (word, self.down[i][1], self.down[i][2], words_to_clues[word])

    def auto_fill_clues(self):
        for i in range(len(self.across)):
            word = self.across[i][0]
            clue = self.across[i][3]
            if not clue:
                self.across[i] = (word, self.across[i][1], self.across[i][2], llm_generate_clue(word, self.prompt))
        for i in range(len(self.down)):
            word = self.down[i][0]
            clue = self.down[i][3]
            if not clue:
                self.down[i] = (word, self.down[i][1], self.down[i][2], llm_generate_clue(word, self.prompt))

    def __str__(self):
        for i in range(self.size):
            for j in range(self.size):
                char = self.eval(self.grid[i][j])
                if char == BLANK:
                    print("*", end=" ")
                else:
                    print(char, end=" ")
            print()
        print()

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