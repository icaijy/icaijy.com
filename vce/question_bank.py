"""Curated VCE Algorithmics multiple-choice bank.

Every item is original wording. The bank is informed by the 2015–2024 VCAA
examinations and the 2023–2027 Study Design; the 2025 paper was used only as a
style check. Keeping the material original makes it safe to publish and lets us
give concise feedback for every distractor.
"""
from dataclasses import dataclass
from random import Random
import re


def latexify(text):
    """Wrap the compact maths used by the bank without changing answer identity."""
    if not isinstance(text, str) or '\\(' in text or '\\[' in text:
        return text
    recurrence = re.search(r'T\(n\) = (\d+)T\(n/(\d+)\) \+ O\(n\^(\d+)\)', text)
    if recurrence:
        plain = recurrence.group(0)
        a, b, c = recurrence.groups()
        text = text.replace(plain, rf'\(T(n)={a}T(n/{b})+O(n^{c})\)')
        return text
    def complexity(match):
        body = match.group(1).replace('log₂ ', r'\log_2 ').replace('log ', r'\log ')
        body = body.replace('²', '^2').replace('³', '^3').replace('ⁿ', '^n').replace('×', r'\times ')
        return rf'\(O({body})\)'
    text = re.sub(r'O\(([^)]+)\)', complexity, text)
    replacements = (
        ('n(n − 1)/2', r'\(n(n-1)/2\)'), ('n − 1', r'\(n-1\)'),
        ('n + 1', r'\(n+1\)'), ('2n', r'\(2n\)'), ('n²', r'\(n^2\)'),
        ('log₂n', r'\(\log_2 n\)'), ('1 + … + n', r'\(1+\cdots+n\)'),
        ('floor((low + high)/2)', r'\(\lfloor(low+high)/2\rfloor\)'),
    )
    for plain, maths in replacements:
        text = text.replace(plain, maths)
    if text.startswith('Compare a = '):
        match = re.fullmatch(r'Compare a = (\d+) with b\^c = (\d+)\.', text)
        if match:
            return rf'Compare \(a={match.group(1)}\) with \(b^c={match.group(2)}\).'
    return text


@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    options: tuple[str, str, str, str]
    answer_index: int
    explanations: tuple[str, str, str, str]
    source: str
    topic: str

    @property
    def answer(self):
        return self.options[self.answer_index]

    def public_dict(self):
        return {'id': self.id, 'prompt': latexify(self.prompt), 'options': tuple(latexify(option) for option in self.options), 'source': self.source, 'topic': self.topic}

    def review_dict(self, selected=None):
        return {
            **self.public_dict(),
            'answer': latexify(self.answer),
            'answer_index': self.answer_index,
            'explanations': tuple(latexify(note) for note in self.explanations),
            'selected': selected,
        }


QUESTIONS = []


def add(slug, prompt, options, answer, explanations, topic):
    if isinstance(answer, str):
        answer = options.index(answer)
    question = Question(
        id=slug,
        prompt=prompt,
        options=tuple(options),
        answer_index=answer,
        explanations=tuple(explanations),
        source=f'Written for icaijy.com · {topic}',
        topic=topic,
    )
    assert len(question.options) == len(question.explanations) == 4
    assert len(set(question.options)) == 4
    QUESTIONS.append(question)


def add_shuffled(slug, prompt, correct, distractors, topic, correct_note, distractor_notes=None):
    pairs = [(correct, correct_note)] + list(zip(distractors, distractor_notes or ['Does not fit this requirement.'] * 3))
    Random(slug).shuffle(pairs)
    add(slug, prompt, [p[0] for p in pairs], correct, [p[1] for p in pairs], topic)


# Abstract data types and modelling
adt_cases = [
    ('adt-membership', 'test quickly whether a username has already been used', 'set', ['stack', 'queue', 'priority queue'], 'A set models unique membership.'),
    ('adt-key-value', 'look up a student record using a student ID', 'dictionary', ['set', 'stack', 'queue'], 'A dictionary maps each key to a value.'),
    ('adt-next-job', 'always process the waiting job with the highest urgency', 'priority queue', ['queue', 'stack', 'set'], 'A priority queue removes the highest-priority item.'),
    ('adt-arrival', 'serve customers in the order in which they arrived', 'queue', ['stack', 'set', 'dictionary'], 'A queue provides first-in, first-out access.'),
    ('adt-undo', 'undo edits in reverse order', 'stack', ['queue', 'set', 'priority queue'], 'A stack provides last-in, first-out access.'),
    ('adt-network', 'represent cities and the roads joining them', 'graph', ['stack', 'dictionary', 'set'], 'A graph models entities and relationships.'),
    ('adt-duplicates', 'store a sequence while preserving duplicates and order', 'list', ['set', 'stack', 'priority queue'], 'A list preserves sequence and permits repeated values.'),
    ('adt-fixed-index', 'access the 18th temperature reading directly', 'array', ['queue', 'stack', 'set'], 'An array supports access by numeric index.'),
]
for i, (slug, task, correct, wrong, note) in enumerate(adt_cases):
    for version, context in enumerate(('A school system must', 'A transport app must', 'A research program must')):
        add_shuffled(f'{slug}-{i}-{version}', f'{context} {task}. Which ADT is most suitable?', correct, wrong, 'U3 AOS1 · ADTs', note)

adt_operations = [
    ('stack-push', 'push', 'stack × item → stack', ['stack → item', 'stack → stack × item', 'item → stack'], 'Push adds an item and returns the updated stack.'),
    ('stack-pop', 'pop', 'stack → stack', ['stack × item → stack', 'stack → item × item', 'item → stack'], 'Pop removes the top item and returns the updated stack in this specification.'),
    ('queue-enqueue', 'enqueue', 'queue × item → queue', ['queue → item', 'queue → queue × item', 'item → queue'], 'Enqueue adds an item to a queue.'),
    ('queue-front', 'front', 'queue → item', ['queue × item → queue', 'item → queue', 'queue → queue × item'], 'Front observes the next item without adding one.'),
    ('set-insert', 'insert', 'set × item → set', ['set → item', 'item → set × set', 'set × set → item'], 'Insert adds one item to the set.'),
    ('dict-lookup', 'lookup', 'dictionary × key → value', ['dictionary × value → key', 'key → dictionary', 'dictionary → key × value'], 'Lookup maps a supplied key to its value.'),
]
for slug, operation, correct, wrong, note in adt_operations:
    add_shuffled(slug, f'Which signature best specifies the {operation} operation?', correct, wrong, 'U3 AOS1 · ADT signatures', note)


# Graph concepts and named graph algorithms
graph_algorithms = [
    ('mst-connect', 'Connect all offices with minimum total cable length.', "Prim's algorithm", ['Dijkstra’s algorithm', 'Floyd–Warshall algorithm', 'PageRank'], 'This is a minimum spanning tree problem.'),
    ('sssp-positive', 'Find shortest distances from one depot when all edge weights are non-negative.', 'Dijkstra’s algorithm', ["Prim's algorithm", 'Floyd–Warshall algorithm', 'PageRank'], 'Dijkstra solves non-negative single-source shortest paths.'),
    ('sssp-negative', 'Find shortest distances from one source where negative edges may occur but no negative cycle exists.', 'Bellman–Ford algorithm', ['Dijkstra’s algorithm', "Prim's algorithm", 'breadth-first search'], 'Bellman–Ford permits negative edge weights.'),
    ('apsp', 'Find shortest distances between every pair of vertices.', 'Floyd–Warshall algorithm', ['Bellman–Ford algorithm', "Prim's algorithm", 'depth-first search'], 'Floyd–Warshall solves all-pairs shortest paths.'),
    ('unweighted-shortest', 'Find a path using the fewest edges in an unweighted graph.', 'breadth-first search', ['depth-first search', "Prim's algorithm", 'PageRank'], 'BFS explores vertices in increasing edge distance.'),
    ('reachability', 'Explore one branch deeply before returning to alternatives.', 'depth-first search', ['breadth-first search', 'Dijkstra’s algorithm', 'PageRank'], 'DFS follows a branch before backtracking.'),
    ('importance', 'Estimate a web page’s importance from links made by other pages.', 'PageRank', ['Floyd–Warshall algorithm', "Prim's algorithm", 'binary search'], 'PageRank estimates importance from incoming links.'),
]
for slug, problem, correct, wrong, note in graph_algorithms:
    add_shuffled(slug, problem + ' Which algorithm is most fit for purpose?', correct, wrong, 'U3 AOS2 · Graph algorithms', note)

graph_facts = [
    ('tree-edges', 'A tree with n vertices has exactly', 'n − 1 edges', ['n edges', 'n + 1 edges', '2n edges'], 'A connected acyclic graph has n − 1 edges.'),
    ('complete-edges', 'An undirected complete graph with n vertices has', 'n(n − 1)/2 edges', ['n² edges', 'n(n + 1)/2 edges', '2n edges'], 'Each unordered pair contributes one edge.'),
    ('connected', 'A graph is connected when', 'every pair of vertices has a path between them', ['every vertex has equal degree', 'it contains no cycle', 'every vertex is adjacent to every other'], 'Connectivity requires paths, not direct edges.'),
    ('subgraph', 'A subgraph may contain', 'subsets of the original vertices and edges', ['new vertices only', 'edges absent from the original graph', 'every original edge only'], 'A subgraph uses only original vertices and edges.'),
    ('weighted', 'In a weighted graph, a weight is usually attached to', 'an edge or vertex to represent a quantity', ['the graph title', 'only isolated vertices', 'the drawing scale'], 'Weights encode cost, distance or another quantity.'),
    ('directed', 'In a directed graph, an edge from u to v', 'does not imply an edge from v to u', ['always implies v to u', 'must have weight 1', 'makes the graph complete'], 'Direction makes adjacency asymmetric.'),
]
for slug, prompt, correct, wrong, note in graph_facts:
    add_shuffled(slug, prompt, correct, wrong, 'U3 AOS1 · Graphs', note)


# Design patterns and algorithm behaviour
patterns = [
    ('pattern-brute', 'systematically examines every candidate solution', 'brute-force search', ['greedy', 'divide and conquer', 'dynamic programming']),
    ('pattern-greedy', 'commits to the locally best available choice at each step', 'greedy', ['backtracking', 'divide and conquer', 'dynamic programming']),
    ('pattern-dc', 'splits a problem into independent smaller instances and combines their answers', 'divide and conquer', ['greedy', 'hill climbing', 'brute-force search']),
    ('pattern-dp', 'stores solutions of overlapping subproblems to avoid recomputation', 'dynamic programming', ['divide and conquer', 'greedy', 'simulated annealing']),
    ('pattern-backtrack', 'abandons a partial candidate as soon as it cannot lead to a valid solution', 'backtracking', ['binary search', 'PageRank', 'hill climbing']),
    ('pattern-hill', 'repeatedly moves to a neighbouring state with a better heuristic value', 'hill climbing', ['breadth-first search', 'dynamic programming', 'divide and conquer']),
    ('pattern-sa', 'sometimes accepts a worse move according to a temperature parameter', 'simulated annealing', ['hill climbing', 'binary search', 'backtracking']),
    ('pattern-astar', 'orders frontier states using cost-so-far plus an estimated remaining cost', 'A*', ['Dijkstra’s algorithm', 'PageRank', "Prim's algorithm"]),
]
for slug, behaviour, correct, wrong in patterns:
    add_shuffled(slug, f'Which design pattern or algorithm {behaviour}?', correct, wrong, 'U3/U4 · Algorithm design patterns', f'This is the defining behaviour of {correct}.')

named_patterns = [
    ('mergesort-pattern', 'mergesort', 'divide and conquer'),
    ('binary-pattern', 'binary search', 'divide and conquer'),
    ('interval-scheduling-pattern', 'the standard earliest-finish-time interval scheduler', 'greedy'),
    ('knapsack-pattern', 'the standard one-dimensional 0–1 knapsack algorithm', 'dynamic programming'),
    ('maze-pattern', 'a recursive maze solver that reverses choices at dead ends', 'backtracking'),
]
for slug, algorithm, correct in named_patterns:
    wrong = [x for x in ('brute-force search', 'greedy', 'divide and conquer', 'dynamic programming', 'backtracking') if x != correct][:3]
    add_shuffled(slug, f'Which design pattern is most clearly used by {algorithm}?', correct, wrong, 'U3/U4 · Algorithm design patterns', f'{algorithm.capitalize()} uses {correct}.')


# Iterative analysis. Each entry deliberately asks about a distinct structural feature.
loop_shapes = [
    ('single', 'For i from 1 to n: constantWork()', 'O(n)', ['O(1)', 'O(log n)', 'O(n²)'], 'The body runs n times.'),
    ('nested', 'For i from 1 to n: For j from 1 to n: constantWork()', 'O(n²)', ['O(n)', 'O(n log n)', 'O(2ⁿ)'], 'There are n × n iterations.'),
    ('triangle', 'For i from 1 to n: For j from 1 to i: constantWork()', 'O(n²)', ['O(n)', 'O(log n)', 'O(n³)'], '1 + … + n is quadratic.'),
    ('halve', 'While n > 1: n ← floor(n/2)', 'O(log n)', ['O(1)', 'O(n)', 'O(n log n)'], 'Repeated halving takes logarithmically many steps.'),
    ('double', 'i ← 1; While i < n: i ← 2i', 'O(log n)', ['O(n)', 'O(n²)', 'O(2ⁿ)'], 'Repeated doubling reaches n after log₂n steps.'),
    ('linear-log', 'For i from 1 to n: j ← 1; While j < n: j ← 2j', 'O(n log n)', ['O(n)', 'O(log n)', 'O(n²)'], 'A logarithmic loop occurs n times.'),
    ('constant-inner', 'For i from 1 to n: For j from 1 to 67: constantWork()', 'O(n)', ['O(1)', 'O(n log n)', 'O(n²)'], '67 is a constant independent of n.'),
    ('two-loops', 'For i from 1 to n: work(); For j from 1 to n: work()', 'O(n)', ['O(1)', 'O(n²)', 'O(2n²)'], 'Sequential linear loops add, not multiply.'),
    ('cube', 'Three nested loops each run from 1 to n.', 'O(n³)', ['O(n)', 'O(n²)', 'O(3n)'], 'The iteration counts multiply.'),
    ('decrement-two', 'While n > 0: n ← n − 2', 'O(n)', ['O(1)', 'O(log n)', 'O(n²)'], 'Dividing the iteration count by constant 2 keeps it linear.'),
]
for slug, code, correct, wrong, note in loop_shapes:
    add_shuffled(f'complexity-{slug}', f'Assume constant-time primitive operations. What is the tightest Big-O bound for: {code}', correct, wrong, 'U4 AOS1 · Time complexity', note)

growth_pairs = [
    ('log-n', 'O(log n)', 'O(n)'), ('n', 'O(n)', 'O(n log n)'), ('nlogn', 'O(n log n)', 'O(n²)'),
    ('square', 'O(n²)', 'O(n³)'), ('cube', 'O(n³)', 'O(2ⁿ)'), ('exp', 'O(2ⁿ)', 'O(n!)'),
]
for slug, faster, slower in growth_pairs:
    candidates = [value for value in ('O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n³)', 'O(2ⁿ)', 'O(n!)') if value not in {faster}]
    slower_candidates = [slower] + [value for value in reversed(candidates) if value != slower]
    add_shuffled(f'growth-{slug}', f'For sufficiently large n, which grows more slowly than {slower}?', faster, slower_candidates[:3], 'U4 AOS1 · Growth rates', f'{faster} has the lower asymptotic growth rate.')


# Recurrences covered by the supplied Master Theorem.
master_cases = [
    (2, 2, 1, 'O(n log n)'),
    (1, 2, 1, 'O(n)'),
    (4, 2, 1, 'O(n²)'),
    (8, 2, 2, 'O(n³)'),
    (3, 3, 1, 'O(n log n)'),
    (1, 3, 0, 'O(log n)'),
    (9, 3, 1, 'O(n²)'),
    (2, 4, 1, 'O(n)'),
    (16, 4, 2, 'O(n² log n)'),
    (4, 4, 0, 'O(n)'),
]
complexity_choices = ['O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(n² log n)', 'O(n³)']
for i, (a, b, c, correct) in enumerate(master_cases):
    wrong = [x for x in complexity_choices if x != correct]
    Random(f'master-{i}').shuffle(wrong)
    add_shuffled(
        f'master-{i}',
        f'Use the supplied Master Theorem. What is T(n) if T(n) = {a}T(n/{b}) + O(n^{c})?',
        correct,
        wrong[:3],
        'U4 AOS1 · Recurrence relations',
        f'Compare a = {a} with b^c = {b ** c}.',
    )


# Binary search traces (30 unique data/target combinations).
for size in (15, 31, 63, 127, 255):
    for target in (1, size // 4, size // 2, 3 * size // 4, size):
        checks = 0
        lo, hi = 1, size
        while lo <= hi:
            checks += 1
            mid = (lo + hi) // 2
            if mid == target:
                break
            if mid < target:
                lo = mid + 1
            else:
                hi = mid - 1
        correct = str(checks)
        alternatives = [str(x) for x in range(1, 10) if x != checks]
        Random(f'bs-{size}-{target}').shuffle(alternatives)
        add_shuffled(
            f'bs-{size}-{target}',
            f'Binary search uses floor((low + high)/2) on the sorted integers 1…{size}. How many values are inspected when searching for {target}?',
            correct,
            alternatives[:3],
            'U4 AOS2 · Binary search',
            f'The midpoint trace reaches {target} after {checks} inspection(s).',
        )


# Correctness, specification and modularity
correctness_items = [
    ('precondition', 'must be true before an algorithm is executed', 'precondition', ['postcondition', 'loop invariant', 'heuristic']),
    ('postcondition', 'must be true when a correct algorithm terminates', 'postcondition', ['precondition', 'counterexample', 'recurrence']),
    ('invariant', 'remains true before and after every loop iteration', 'loop invariant', ['postcondition', 'input size', 'base case']),
    ('termination', 'establishes that an algorithm cannot continue forever', 'termination argument', ['test case', 'heuristic value', 'ADT signature']),
    ('counterexample', 'is a single valid input that disproves a universal correctness claim', 'counterexample', ['postcondition', 'benchmark', 'base case']),
    ('induction', 'proves a recursive claim from a base case and a smaller instance', 'inductive argument', ['random testing', 'hill climbing', 'simulation']),
    ('module', 'hides implementation details behind specified operations', 'abstraction', ['brute force', 'recursion depth', 'graph density']),
]
for slug, definition, correct, wrong in correctness_items:
    add_shuffled(f'correct-{slug}', f'Which term {definition}?', correct, wrong, 'U3 AOS2 · Correctness and modularity', f'This describes a {correct}.')

add_shuffled('testing-proof', 'Why can testing many inputs usually not prove that an algorithm is correct for every valid input?', 'Untested valid inputs may still fail.', ['Testing always changes the algorithm.', 'Big-O notation forbids testing.', 'Only recursive algorithms can be tested.'], 'U3 AOS2 · Correctness', 'A finite test set need not cover the whole input domain.')
add_shuffled('greedy-proof', 'A greedy algorithm is claimed to be optimal. Which evidence is strongest?', 'A proof that every greedy choice can be part of an optimal solution.', ['It worked on ten random inputs.', 'Its code is short.', 'It uses a priority queue.'], 'U3 AOS2 · Correctness', 'An exchange-style argument establishes optimality generally.')


# Complexity classes, reductions and practical limits.
complexity_class_items = [
    ('class-p', 'decision problems solvable in polynomial time', 'P', ['NP', 'NP-Hard', 'undecidable']),
    ('class-np', 'decision problems whose yes-instances have polynomial-time verifiable certificates', 'NP', ['P only', 'NP-Hard only', 'undecidable']),
    ('class-npc', 'problems that are both in NP and NP-Hard', 'NP-Complete', ['P', 'NP', 'exponential']),
    ('class-nph', 'problems at least as hard as every problem in NP, without a requirement that they be in NP', 'NP-Hard', ['P', 'NP only', 'NP-Complete only']),
]
for slug, definition, correct, wrong in complexity_class_items:
    add_shuffled(slug, f'Which class is best described as {definition}?', correct, wrong, 'U4 AOS1 · P, NP and reductions', f'That is the definition of {correct}.')

reduction_items = [
    ('reduce-direction', 'To show new problem X is NP-Hard using known NP-Hard problem Y, the required polynomial reduction direction is', 'Y → X', ['X → Y', 'X → P', 'P → Y'], 'Solving X would then solve Y.'),
    ('p-equals-np', 'If one NP-Complete problem is shown to have a polynomial-time algorithm, then', 'P = NP', ['P ≠ NP', 'only that problem enters P', 'all NP-Hard problems become decidable'], 'Every NP problem reduces to that NP-Complete problem.'),
    ('certificate', 'For a decision version of travelling salesperson, a natural certificate is', 'a proposed tour whose length can be checked', ['the source code of every algorithm', 'a proof that P ≠ NP', 'an unsorted list of edge weights'], 'A proposed tour can be verified in polynomial time.'),
    ('soft-limit', 'An exponential-time algorithm on large inputs illustrates', 'a soft limit of computability', ['an undecidable problem', 'a syntax error', 'a violation of Church–Turing'], 'The problem is computable but may be impractical.'),
    ('worst-case', 'Worst-case time complexity gives', 'an upper bound over all inputs of a given size', ['the exact time on every device', 'the average over one dataset', 'the memory used by the best input'], 'Worst case considers the most costly input of each size.'),
]
for slug, prompt, correct, wrong, note in reduction_items:
    add_shuffled(slug, prompt, correct, wrong, 'U4 AOS1 · Complexity limits', note)


# Computability and the history/philosophy named by the Study Design.
computability = [
    ('tm-tape', 'In the standard model, a Turing machine reads and writes symbols on', 'an unbounded tape divided into cells', ['a finite queue only', 'a weighted graph', 'a neural network']),
    ('tm-transition', 'A Turing machine transition depends on', 'the current state and scanned symbol', ['the wall-clock time only', 'the entire future tape', 'a random training label']),
    ('halting', 'The Halting Problem asks whether', 'a program eventually stops on a given input', ['a graph is connected', 'two arrays have equal length', 'a model is unbiased']),
    ('halting-result', 'The general Halting Problem is', 'undecidable', ['NP-Complete', 'solved by binary search', 'linear time']),
    ('church-turing', 'The Church–Turing thesis informally claims that', 'every effectively calculable function can be computed by a Turing machine', ['every true statement is provable', 'P equals NP', 'all programs halt']),
    ('lambda', 'Lambda calculus is important in computability because it', 'provides a model of computation equivalent in power to Turing machines', ['sorts only numeric arrays', 'proves all algorithms efficient', 'requires machine learning']),
    ('entscheidungsproblem', 'The negative resolution of the Entscheidungsproblem showed that', 'no single algorithm decides validity for every statement in first-order logic', ['all mathematical claims are false', 'every program can be tested exhaustively', 'NP-Complete problems are undecidable']),
    ('hard-limit', 'An undecidable problem represents', 'a hard limit of computability', ['a constant-factor slowdown', 'a poor choice of data structure', 'an average-case analysis']),
]
for slug, prompt, correct, wrong in computability:
    add_shuffled(slug, prompt, correct, wrong, 'U4 AOS3 · Computability', f'The accepted statement is: {correct}.')


# Machine learning, AI and ethics.
ml_items = [
    ('supervised', 'learns from examples paired with desired outputs', 'supervised learning', ['unsupervised learning', 'binary search', 'PageRank']),
    ('unsupervised', 'seeks structure in unlabelled data', 'unsupervised learning', ['supervised learning', 'backtracking', 'formal verification']),
    ('training', 'adjusts a model using data before it is used for predictions', 'training', ['inference', 'decomposition', 'halting']),
    ('inference', 'uses a trained model to produce an output for new data', 'inference', ['training', 'annotation', 'recursion']),
    ('decision-tree', 'makes predictions by following feature-based branches', 'decision tree', ['support vector machine', 'neural network', 'Turing machine']),
    ('svm', 'separates classes using a maximum-margin boundary', 'support vector machine', ['decision tree', 'queue', 'simulated annealing']),
    ('neural', 'uses weighted connections arranged in layers', 'neural network', ['decision tree', 'minimum spanning tree', 'stack']),
    ('overfit', 'performs very well on training examples but poorly on new examples', 'overfitting', ['underflow', 'abstraction', 'backtracking']),
]
for slug, description, correct, wrong in ml_items:
    add_shuffled(f'ml-{slug}', f'Which term best matches a system that {description}?', correct, wrong, 'U4 AOS3 · Data-driven algorithms', f'This describes {correct}.')

ai_items = [
    ('turing-test', 'A text-only interrogator tries to distinguish a human from a machine.', 'Turing Test', ['Halting Problem', 'Chinese Room', 'Church–Turing thesis']),
    ('chinese-room', 'A person follows symbol rules without understanding the language.', 'Chinese Room argument', ['Turing Test', 'PageRank', 'Master Theorem']),
    ('weak-ai', 'A system is designed to perform a specific apparently intelligent task.', 'weak AI', ['strong AI', 'undecidability', 'NP-Completeness']),
    ('strong-ai', 'A machine genuinely possesses a mind or understanding.', 'strong AI', ['weak AI', 'supervised learning', 'graph search']),
]
for slug, description, correct, wrong in ai_items:
    add_shuffled(f'ai-{slug}', f'Which concept is illustrated? {description}', correct, wrong, 'U4 AOS3 · Conceptions of AI', f'This is the standard description of {correct}.')

ethics_items = [
    ('bias-sample', 'A face-recognition model works poorly for a group scarcely represented in its training set.', 'bias from unrepresentative data', ['guaranteed neutrality', 'a proof of correctness', 'a faster runtime']),
    ('transparency', 'A loan applicant is told what major factors affected an automated decision.', 'transparency', ['graph connectivity', 'recursion', 'data compression']),
    ('accountability', 'An organisation names who is responsible for harms caused by its model.', 'accountability', ['anonymity', 'overfitting', 'memoisation']),
    ('privacy', 'Training records reveal identifiable medical information.', 'privacy risk', ['minimum spanning tree', 'termination proof', 'time complexity']),
    ('feedback', 'Past biased policing data directs more patrols to the same areas, generating more similar data.', 'a harmful feedback loop', ['binary search', 'a balanced dataset', 'formal verification']),
    ('proxy', 'A postcode indirectly encodes socioeconomic or ethnic background.', 'a proxy variable may reproduce discrimination', ['the feature is automatically fair', 'the model becomes unsupervised', 'the algorithm becomes undecidable']),
    ('automation-bias', 'A human accepts a model output despite strong contradictory evidence.', 'automation bias', ['divide and conquer', 'space complexity', 'an invariant']),
    ('consent', 'Personal messages are used as training data without users being informed.', 'lack of informed consent', ['a complete graph', 'a polynomial reduction', 'dynamic programming']),
]
for slug, scenario, correct, wrong in ethics_items:
    add_shuffled(f'ethics-{slug}', scenario + ' What is the most relevant issue?', correct, wrong, 'U4 AOS3 · AI ethics', f'The scenario directly illustrates {correct}.')


# Heuristic behaviour and dynamic programming details.
advanced_items = [
    ('astar-admissible', 'An admissible A* heuristic', 'never overestimates the remaining optimal cost', ['must always equal zero', 'always overestimates the cost', 'depends only on elapsed time'], 'This condition preserves optimality.'),
    ('astar-zero', 'If A* uses h(n) = 0 for every node with non-negative edge weights, it behaves like', 'Dijkstra’s algorithm', ['depth-first search', "Prim's algorithm", 'PageRank'], 'Then priority is cost-so-far only.'),
    ('hill-local', 'A basic hill-climbing search may stop before the global optimum because of', 'a local optimum', ['a guaranteed negative cycle', 'a queue overflow by definition', 'the Master Theorem'], 'No improving neighbour may exist at a non-global optimum.'),
    ('sa-temperature', 'As simulated annealing temperature decreases, accepting a worse move generally becomes', 'less likely', ['more likely', 'certain', 'unrelated to temperature'], 'Cooling gradually reduces exploratory worse moves.'),
    ('dp-state', 'A useful dynamic-programming state should contain', 'enough information to determine future transitions', ['every line of source code', 'only the final answer', 'a random heuristic'], 'The state summarises relevant history.'),
    ('memo', 'Memoisation is', 'top-down recursion with cached subproblem results', ['a graph traversal without storage', 'a greedy proof', 'a hardware optimisation only'], 'Memoisation caches recursive results.'),
    ('tabulation', 'Tabulation is usually', 'bottom-up evaluation of DP states', ['randomised backtracking', 'a Turing Test', 'a reduction proof'], 'Tabulation fills a table in dependency order.'),
    ('backtrack-prune', 'Backtracking gains efficiency mainly by', 'pruning partial candidates that cannot succeed', ['checking every completion anyway', 'removing all base cases', 'using only negative edges'], 'Pruning avoids exploring impossible branches.'),
]
for slug, prompt, correct, wrong, note in advanced_items:
    add_shuffled(slug, prompt, correct, wrong, 'U4 AOS2 · Advanced design', note)


# Parallel variants test the same syllabus points in fresh contexts without copying VCAA wording.
contextual_cases = [
    ('network-cables', 'A council must connect all suburbs while minimising total new cable.', "Prim's algorithm", 'graph algorithms'),
    ('negative-fares', 'A fare graph includes rebates represented by negative edges and has no negative cycle.', 'Bellman–Ford algorithm', 'graph algorithms'),
    ('all-campus', 'A campus planner needs shortest walking distances between every pair of buildings.', 'Floyd–Warshall algorithm', 'graph algorithms'),
    ('urgent-patients', 'Patients must be treated according to changing urgency scores.', 'priority queue', 'ADTs'),
    ('browser-back', 'A browser must return through previously visited pages in reverse order.', 'stack', 'ADTs'),
    ('duplicate-check', 'A form must reject an ID if it is already present.', 'set', 'ADTs'),
    ('route-heuristic', 'A route finder combines distance travelled with estimated distance remaining.', 'A*', 'advanced design'),
    ('unknown-clusters', 'A system groups articles without any supplied category labels.', 'unsupervised learning', 'data-driven algorithms'),
    ('spam-labels', 'A classifier learns from emails already labelled spam or not spam.', 'supervised learning', 'data-driven algorithms'),
    ('explain-rejection', 'A bank provides understandable reasons for an automated rejection.', 'transparency', 'AI ethics'),
]
all_choices = {
    'graph algorithms': ["Prim's algorithm", 'Dijkstra’s algorithm', 'Bellman–Ford algorithm', 'Floyd–Warshall algorithm', 'PageRank'],
    'ADTs': ['set', 'dictionary', 'stack', 'queue', 'priority queue'],
    'advanced design': ['A*', 'hill climbing', 'simulated annealing', 'dynamic programming', 'backtracking'],
    'data-driven algorithms': ['supervised learning', 'unsupervised learning', 'binary search', 'PageRank', 'backtracking'],
    'AI ethics': ['transparency', 'accountability', 'bias', 'privacy', 'time complexity'],
}
for case_slug, scenario, correct, family in contextual_cases:
    pool = [x for x in all_choices[family] if x != correct]
    for version, lead in enumerate(('Which tool is most fit for purpose?', 'Which concept best matches this situation?', 'Select the best model or method.')):
        Random(f'{case_slug}-{version}').shuffle(pool)
        add_shuffled(f'context-{case_slug}-{version}', f'{scenario} {lead}', correct, pool[:3], f'Applied · {family}', f'{correct} directly matches the stated requirement.')


# Fast numerical drills: these reward fluent execution, which matters in a one-minute format.
for vertices in range(4, 19):
    correct_edges = vertices * (vertices - 1) // 2
    distractors = [vertices - 1, vertices * (vertices - 1), vertices * vertices]
    add_shuffled(
        f'complete-count-{vertices}',
        f'How many edges are in an undirected complete graph with {vertices} vertices?',
        str(correct_edges),
        [str(value) for value in distractors],
        'U3 AOS1 · Graph modelling',
        f'There is one edge for each unordered pair: {vertices}×{vertices - 1}/2 = {correct_edges}.',
    )

for items in (8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384):
    comparisons = items.bit_length()
    add_shuffled(
        f'binary-worst-{items}',
        f'Using the usual inclusive low/high implementation, at most how many element inspections can an unsuccessful binary search of {items} sorted items require?',
        str(comparisons),
        [str(comparisons - 1), str(comparisons + 1), str(items)],
        'U4 AOS2 · Binary search',
        f'An unsuccessful search may inspect floor(log₂({items})) + 1 = {comparisons} elements.',
    )

for version, rows in enumerate((
    ((2, 8), (3, 5), (4, 6), (5, 3)),
    ((1, 9), (4, 4), (6, 2), (7, 1)),
    ((3, 7), (5, 6), (7, 3), (8, 2)),
    ((2, 10), (6, 5), (9, 1), (4, 8)),
    ((5, 8), (8, 4), (4, 10), (9, 3)),
    ((1, 12), (3, 9), (5, 5), (7, 2)),
    ((4, 11), (6, 7), (8, 4), (10, 1)),
    ((2, 14), (5, 8), (9, 3), (11, 2)),
    ((3, 15), (7, 6), (10, 2), (12, 1)),
    ((4, 12), (8, 5), (11, 3), (13, 0)),
)):
    scores = [g + h for g, h in rows]
    answer_index = min(range(4), key=scores.__getitem__)
    options = [f'Node {chr(65 + i)}: g = {g}, h = {h}, f = {g + h}' for i, (g, h) in enumerate(rows)]
    add(
        f'astar-order-{version}',
        'A* uses f(n) = g(n) + h(n). Which frontier node should it expand next?',
        options,
        answer_index,
        [f'f = {score}; ' + ('this is minimal.' if i == answer_index else 'another node has a smaller f.') for i, score in enumerate(scores)],
        'U4 AOS2 · A* search',
    )

for version, priorities in enumerate((
    (2, 9, 5, 7), (14, 3, 8, 6), (1, 4, 12, 10), (17, 11, 15, 2),
    (6, 13, 9, 4), (20, 16, 18, 7), (5, 2, 8, 3), (21, 19, 22, 12),
    (7, 14, 11, 13), (25, 23, 9, 24),
)):
    labels = ['A', 'B', 'C', 'D']
    best = max(range(4), key=priorities.__getitem__)
    options = [f'Job {label} (priority {priority})' for label, priority in zip(labels, priorities)]
    add(
        f'pq-trace-{version}',
        'A max-priority queue removes the numerically highest priority first. Which job is removed?',
        options,
        best,
        [('This has the highest priority.' if i == best else 'A higher-priority job is present.') for i in range(4)],
        'U3 AOS1 · Priority queues',
    )

operation_rates = [
    ('linear-million', 'O(n)', 1_000_000, 'about 1 million'),
    ('square-million', 'O(n²)', 1_000_000, 'about 1 trillion'),
    ('cube-thousand', 'O(n³)', 1_000, 'about 1 billion'),
    ('log-billion', 'O(log₂ n)', 1_000_000_000, 'about 30'),
    ('nlog-million', 'O(n log₂ n)', 1_000_000, 'about 20 million'),
]
for slug, order, n, correct in operation_rates:
    operation_choices = ['about 30', 'about 1 thousand', 'about 1 million', 'about 20 million', 'about 1 billion', 'about 1 trillion', 'about 1 quadrillion']
    distractors = [value for value in operation_choices if value != correct]
    Random(slug).shuffle(distractors)
    add_shuffled(
        f'operations-{slug}',
        f'Ignoring constant factors, approximately how many primitive operations does an {order} algorithm perform when n = {n:,}?',
        correct,
        distractors[:3],
        'U4 AOS1 · Practical complexity',
        f'Substitute n into the stated growth function.',
    )

search_comparisons = [
    ('sorted-static', 'Many membership queries on a large sorted array.', 'binary search', ['linear search', 'depth-first search', 'hill climbing']),
    ('tiny-once', 'One lookup in an unsorted list of five items.', 'linear search', ['Floyd–Warshall', 'PageRank', "Prim's algorithm"]),
    ('unknown-tree', 'Explore a game tree and undo choices when a dead end is reached.', 'backtracking', ['binary search', 'PageRank', 'mergesort']),
    ('best-neighbour', 'Improve a timetable by repeatedly accepting only a better neighbouring timetable.', 'hill climbing', ['breadth-first search', 'binary search', 'dynamic programming']),
    ('escape-local', 'Optimise a timetable while occasionally accepting worse moves early in the search.', 'simulated annealing', ['hill climbing', 'binary search', 'Floyd–Warshall']),
]
for slug, situation, correct, wrong in search_comparisons:
    for version, suffix in enumerate(('Which approach is most suitable?', 'Choose the best algorithmic description.')):
        add_shuffled(f'search-choice-{slug}-{version}', f'{situation} {suffix}', correct, wrong, 'U4 AOS2 · Selecting algorithms', f'{correct} best matches the input and goal.')


QUESTION_BY_ID = {question.id: question for question in QUESTIONS}
assert len(QUESTION_BY_ID) == len(QUESTIONS), 'Question IDs must be unique.'
