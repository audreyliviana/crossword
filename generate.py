import sys
import collections

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.domains:
            to_remove = set()
            for value in self.domains[var]:
                if len(value) != var.length:
                    to_remove.add(value)
            for value in to_remove:
                self.domains[var].remove(value)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        overlap = self.crossword.overlaps.get((x, y))
        if not overlap:
            return False
        i, j = overlap
        to_remove = set()
        for x_value in self.domains[x]:
            if not any(x_value[i] == y_value[j] for y_value in self.domains[y]):
                to_remove.add(x_value)
        for x_value in to_remove:
            self.domains[x].remove(x_value)
            revised = True
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        # change arcs to deque for efficient popleft
        if arcs is None:
            arcs = collections.deque((x, y) for x in self.domains for y in self.domains if x != y)
        else:
            arcs = collections.deque(arcs)
        
        # revise each arc one at a time, add additional arcs to queue to ensure that other arcs stay consistent
        while arcs:
            x, y = arcs.popleft()
            if self.revise(x, y):
                if not self.domains[x]:
                    return False
                # because we don't want to revise z anymore, x is put second in the tuple to not revise it
                for z in self.crossword.neighbors(x) - set([y]):
                    arcs.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.crossword.variables:
            if var not in assignment or assignment[var] is None:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check all values are distinct
        values = list(assignment.values())
        if len(values) != len(set(values)):
            return False
        
        for var, value in assignment.items():
            # check if value has the correct length
            if len(value) != var.length:
                return False
            # check for conflicts with neighboring variables
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    overlap = self.crossword.overlaps[var, neighbor]
                    if overlap:
                        i, j = overlap
                        if value[i] != assignment[neighbor][j]:
                            return False
        
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        def count_conflicts(value):
            conflicts = 0
            for neighbor in self.crossword.neighbors(var):
                # any var present in assignment already has a value and shouldn't be counted when computing the number of values ruled out for neighboring unassigned variables.
                if neighbor not in assignment:
                    overlap = self.crossword.overlaps[var, neighbor]
                    if overlap:
                        i, j = overlap
                        for neighbor_val in self.domains[neighbor]:
                            if value[i] != neighbor_val[j]:
                                conflicts += 1
            return conflicts
        
        # return the domain values sorted by the number of conflicts they cause
        return sorted(self.domains[var], key = count_conflicts)


    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned = [var for var in self.crossword.variables if var not in assignment]
        # function to calculate the number of remaining values (minimum remaining values MRV heuristic)
        def mrv(var):
            return len(self.domains[var])
        # function to calculate the degree (number of neighbors)
        def degree(var):
            return len(self.crossword.neighbors(var))
        return min(unassigned, key = lambda var: (mrv(var), -degree(var)))

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # if the assignment is complete, return it
        if self.assignment_complete(assignment):
            return assignment
        # select an unsigned variable
        var = self.select_unassigned_variable(assignment)
        # order domain values using the least-constraining value heuristic
        for value in self.order_domain_values(var, assignment):
            # create a copy of the assignment and add the variable
            new_assignment = assignment.copy()
            new_assignment[var] = value
            # check if assignment is consistent
            if self.consistent(new_assignment):
                # apply AC3 to maintain arc consistency
                if self.ac3([(var, neighbor) for neighbor in self.crossword.neighbors(var)]):
                    result = self.backtrack(new_assignment)
                    if result:
                        return result
        return None

        


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
