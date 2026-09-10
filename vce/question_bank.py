"""VCE Algorithmics multiple-choice question bank.

All questions are original, written for icaijy.com after reviewing VCAA Section A
papers from 2015–2025 and the 2023–2026 study design/support materials. The 2025
paper is style reference only and contributes no questions to this bank.
"""
from __future__ import annotations

import math

LETTERS = "ABCD"
SOURCE = "ChatGPT · original for icaijy.com"
_qs = []


def q(topic, stem, options, answer, explanation):
    options = [str(x) for x in options]
    if len(options) != 4 or answer not in LETTERS:
        raise ValueError("bad question")
    explanations = ["Not the best answer."] * 4
    explanations[LETTERS.index(answer)] = explanation
    _qs.append({
        "topic": topic, "stem": stem, "options": options, "answer": answer,
        "explanations": explanations, "source": SOURCE,
    })


def rotated(topic, stem, options, correct, explanation, shift=0):
    options = [str(x) for x in options]
    options = options[shift % 4:] + options[:shift % 4]
    q(topic, stem, options, LETTERS[options.index(str(correct))], explanation)


FACTS = [
("u3_adt","Which ADT processes items first-in, first-out?",["stack","queue","set","dictionary"],"B","A queue is FIFO."),
("u3_adt","Which ADT processes the most recently inserted item first?",["array","queue","stack","graph"],"C","A stack is LIFO."),
("u3_adt","Which ADT best maps each student ID to one student record?",["dictionary","queue","stack","set"],"A","A dictionary maps keys to values."),
("u3_adt","Which ADT best represents unique membership when order is irrelevant?",["queue","set","stack","array"],"B","A set models unique membership."),
("u3_adt","Which ADT best supports repeatedly removing the highest-priority job?",["queue","priority queue","stack","set"],"B","A priority queue orders removal by priority."),
("u3_adt","Which ADT most naturally models direct flights between airports?",["graph","stack","queue","set"],"A","Airports are vertices and flights are edges."),
("u3_adt","Which structure most naturally models a strict parent-child hierarchy with one root and no cycles?",["dictionary","queue","tree","set"],"C","That is a tree."),
("u3_adt","What does an ADT specification primarily describe?",["memory addresses","operations and behaviour","CPU instructions","source-code indentation"],"B","ADTs specify an interface and behaviour, not an implementation."),
("u3_adt","Which is an implementation detail rather than an abstract queue operation?",["enqueue","dequeue","front","store items in a circular array"],"D","The circular array is a concrete representation."),
("u3_adt","For contains(set,item), which output type is most appropriate?",["set","boolean","integer always","queue"],"B","Membership is a true/false result."),
("u3_adt","Which queue operation observes the first item without removing it?",["front","dequeue","enqueue","newQueue"],"A","front/peek observes the first item."),
("u3_adt","Which stack operation changes the stack by adding an item?",["top","isEmpty","push","size"],"C","push inserts an item."),
("u3_adt","A road network has distances and every road works both ways. Which graph model is most natural?",["directed unweighted","directed weighted","undirected weighted","undirected unweighted"],"C","Road direction is symmetric and distances are weights."),
("u3_adt","A social-media follows relation is most naturally modelled by a",["directed graph","undirected graph","queue","stack"],"A","Following need not be reciprocal."),
("u3_adt","A state graph for a puzzle normally represents",["configurations as vertices and legal moves as edges","source lines as vertices","only scores as vertices","a FIFO list"],"A","States are vertices; legal transitions are edges."),
("u3_adt","A decision tree is most useful for modelling",["a sequence of tests whose outcomes choose later branches","FIFO service","an MST only","a stack trace only"],"A","Branches naturally encode conditional decisions."),
("u3_graph","Which statement holds for every tree with n ≥ 1 vertices?",["it has n edges","it has n−1 edges","every degree is 2","it contains a cycle"],"B","A tree with n vertices has n−1 edges."),
("u3_graph","A DAG is a directed graph that",["has no directed cycles","has no edges","has exactly one source","must be a tree"],"A","DAG means directed acyclic graph."),
("u3_graph","In an undirected graph, a vertex's degree is",["number of incident edges","number of all vertices","sum of all weights","longest path length"],"A","Degree counts incident edges."),
("u3_graph","For a directed edge u→v, which is correct?",["out-degree(u)+=1 and in-degree(v)+=1","in-degree(u)+=1 and out-degree(v)+=1","degree(u)+=2 only","degrees do not change"],"A","Direction leaves u and enters v."),
("u3_graph","Which representation is usually convenient for iterating neighbours in a sparse graph?",["adjacency list","call stack","truth table","priority value"],"A","Adjacency lists store neighbours directly."),
("u3_graph","A connected component of an undirected graph is",["a maximal mutually reachable vertex set","any single edge","an MST","a directed cycle"],"A","That is the definition of a connected component."),
("u3_graph","Which must hold for a subgraph H of G?",["H may add new vertices","every H edge belongs to G","H contains every G vertex","H is connected"],"B","A subgraph uses subsets of G's vertices/edges."),
("u3_graph","A complete undirected graph has",["an edge between every pair of distinct vertices","degree 1 everywhere","no cycles","equal weights"],"A","Completeness means every vertex pair is adjacent."),
("u3_graph_alg","Which ADT most naturally provides the frontier for BFS?",["queue","stack","dictionary only","set only"],"A","FIFO order gives layer-by-layer exploration."),
("u3_graph_alg","DFS is most naturally associated with",["queue","stack or recursion","priority queue by distance","SVM"],"B","DFS follows one branch deeply using stack behaviour."),
("u3_graph_alg","BFS on an unweighted graph can directly find",["fewest-edge distances from a source","an arbitrary weighted MST","PageRank","all-pairs weighted distances"],"A","BFS layers correspond to unweighted distance."),
("u3_graph_alg","Prim's algorithm finds a",["minimum spanning tree","single-source shortest-path tree necessarily","graph colouring","topological order"],"A","Prim is a greedy MST algorithm."),
("u3_graph_alg","Dijkstra is a standard choice for",["single-source shortest paths with non-negative edge weights","MST only","negative-cycle detection only","sorting"],"A","Dijkstra's standard guarantee requires non-negative weights."),
("u3_graph_alg","Bellman–Ford is especially useful because it",["handles negative edge weights and can detect reachable negative cycles","requires all weights 1","only works on trees","finds MSTs"],"A","Repeated relaxation handles negative weights."),
("u3_graph_alg","Floyd–Warshall computes",["all-pairs shortest paths","one MST","one DFS tree","a stack order"],"A","Floyd–Warshall is an all-pairs dynamic-programming algorithm."),
("u3_graph_alg","Standard Floyd–Warshall runs in",["O(V)","O(V log V)","O(V²)","O(V³)"],"D","It uses three nested loops over vertices."),
("u3_graph_alg","PageRank primarily assigns",["relative importance scores to nodes in a directed network","MST weights","graph colours","queue priorities only"],"A","PageRank ranks nodes using link structure."),
("u3_design","Brute force is best characterised by",["systematically considering all candidate solutions","always taking a locally best choice","splitting only into equal halves","training a model"],"A","Brute force exhaustively explores candidates."),
("u3_design","A greedy algorithm generally",["takes a locally optimal choice at each step","tests every complete candidate","must recurse","is optimal for every problem"],"A","Greedy makes local choices; optimality needs justification."),
("u3_design","Which statement about greedy algorithms is safest?",["they are always optimal","they may be fast but need proof/argument that local choices are suitable","they are always exponential","they are dynamic programming"],"B","Greedy correctness is problem-dependent."),
("u3_design","Modular design primarily helps by",["decomposing a solution into clear components/functions","making everything recursive","removing all data structures","guaranteeing O(1) time"],"A","Modules improve structure, reasoning and reuse."),
("u3_design","A proof by contradiction begins by",["assuming the negation of the desired claim","testing random cases","assuming only the desired claim","running BFS"],"A","Contradiction assumes the opposite and derives impossibility."),
("u3_design","Testing an algorithm on many inputs",["is evidence but not generally a proof for all inputs","always proves correctness","proves only Big-O","is induction"],"A","Finite testing does not cover all possible inputs."),
("u3_design","A recursive algorithm needs",["a base case that eventually stops recursion","a priority queue","a graph","a random seed"],"A","Without a terminating base case recursion may not stop."),
("u3_design","Pseudocode is useful because it",["communicates algorithmic logic without depending heavily on one language","executes faster than machine code","removes data modelling","proves NP-completeness"],"A","Pseudocode is language-light communication."),
("u4_complexity","Big-O primarily describes",["asymptotic growth of resource use","exact CPU nanoseconds","correctness","the language used"],"A","Big-O abstracts constant factors and hardware."),
("u4_complexity","Which grows asymptotically fastest?",["log n","n","n²","2ⁿ"],"D","Exponential growth dominates these polynomial/logarithmic functions."),
("u4_complexity","Which is polynomial in n?",["n³+7n","2ⁿ","n!","3^(n/2)"],"A","A finite sum of fixed powers of n is polynomial."),
("u4_complexity","Two consecutive O(n) loops give total time",["O(1)","O(n)","O(n²)","O(2ⁿ)"],"B","O(n)+O(n)=O(n)."),
("u4_complexity","Two n-iteration loops nested inside each other give",["O(log n)","O(n)","O(n log n)","O(n²)"],"D","The body runs n×n times."),
("u4_complexity","Binary search has worst-case time",["O(1)","O(log n)","O(n)","O(n²)"],"B","The remaining interval halves each comparison."),
("u4_complexity","Mergesort has worst-case time",["O(log n)","O(n)","O(n log n)","O(n²)"],"C","There are logarithmic levels with linear total merge work per level."),
("u4_complexity","Naïve quicksort can degrade to",["O(log n)","O(n)","O(n log n)","O(n²)"],"D","Repeated highly unbalanced partitions yield quadratic work."),
("u4_complexity","Which statement about feasibility is correct?",["every P algorithm is practical","every NP-hard instance is impossible","growth class matters but constants/input sizes still matter","only exponential algorithms can be fast"],"C","Complexity classes do not determine every practical runtime."),
("u4_classes","P is the class of decision problems that",["have deterministic polynomial-time algorithms","cannot be verified","are all NP-hard","require exponential time"],"A","That is the standard definition of P."),
("u4_classes","NP can be characterised as decision problems whose yes-certificates",["can be verified in polynomial time","can never be checked","are always short but exponentially verified","must be graphs"],"A","Polynomial-time verification is the certificate view of NP."),
("u4_classes","Which inclusion is known?",["P⊆NP","NP⊆P","NP-hard⊆P","P and NP are disjoint"],"A","A polynomial-time solver also gives polynomial verification."),
("u4_classes","An NP-complete problem is",["in NP and NP-hard","in P but not NP","undecidable by definition","NP-hard but never in NP"],"A","NP-complete means both membership in NP and NP-hardness."),
("u4_classes","An NP-hard problem",["must be in NP","is at least as hard as every NP problem under the relevant reductions","must be a decision problem","must be undecidable"],"B","NP-hardness does not require membership in NP."),
("u4_classes","If any NP-complete problem is in P, then",["P=NP","P≠NP","the Halting Problem is decidable","NP is empty"],"A","Every NP problem reduces to an NP-complete problem."),
("u4_classes","The phrase 'NP means non-polynomial' is",["correct","incorrect","correct only for graphs","the definition of NP-hard"],"B","NP refers to nondeterministic polynomial time / polynomial verification."),
("u4_classes","To prove X NP-complete, the usual ingredients are",["X∈NP and a known NP-hard problem reduces to X","show one slow implementation","show X undecidable","show X recurses"],"A","Membership plus polynomial-time hardness reduction is the standard framework."),
("u4_divide","Binary search requires",["an ordering that lets half the candidates be discarded","negative cycles","random labels only","a stack-only interface"],"A","Ordering enables the halving decision."),
("u4_divide","Mergesort uses divide and conquer by",["splitting, recursively sorting parts, then merging","taking one local choice and stopping","testing every permutation","training data"],"A","That is the divide/solve/combine structure."),
("u4_divide","Quicksort's divide step usually",["partitions around a pivot","merges two sorted halves","relaxes all graph edges","fills a DP table"],"A","Partitioning places elements relative to a pivot."),
("u4_dp","Dynamic programming is especially useful with",["overlapping subproblems whose results can be reused","no repeated subproblems or structure","undecidable specifications","only one possible input"],"A","DP stores and reuses repeated subproblem results."),
("u4_dp","A DP Fibonacci algorithm beats naïve recursion mainly by",["avoiding repeated recomputation","making Fibonacci numbers smaller","using BFS","making it NP-hard"],"A","Previously computed values are reused."),
("u4_dp","For change making, a state dp[x] naturally represents",["a best/feasible result for amount x","a source-code line","vertex degree only","a Turing transition"],"A","The amount is the one-dimensional subproblem."),
("u4_backtracking","Backtracking can improve over pure enumeration by",["pruning partial candidates that cannot lead to a valid/better solution","solving every NP-hard problem in polynomial time","working only on arrays","avoiding search trees"],"A","Constraint-based pruning avoids useless descendants."),
("u4_backtracking","In graph-colouring backtracking, prune when",["two adjacent assigned vertices already have the same forbidden colour","all vertices are uncoloured","the graph has an edge","a random value is even"],"A","That partial assignment already violates the constraint."),
("u4_heuristic","A heuristic is often used for hard optimisation because it",["can find useful solutions quickly without guaranteeing the optimum","proves P=NP","always enumerates everything","makes a problem undecidable"],"A","Heuristics trade guarantees for practical speed."),
("u4_heuristic","Hill climbing usually moves to",["an improving neighbouring solution","every solution simultaneously","a Turing tape","an MST root"],"A","It is local search over neighbours."),
("u4_heuristic","A key weakness of hill climbing is",["getting stuck at a local optimum","never evaluating neighbours","only solving shortest paths","requiring negative cycles"],"A","Local optima can block progress toward a better global solution."),
("u4_heuristic","Simulated annealing can differ from hill climbing by",["sometimes accepting worse moves","guaranteeing the global optimum in fixed time","avoiding randomness","sorting only"],"A","Worse moves can help escape local optima."),
("u4_heuristic","As simulated-annealing temperature falls, it generally becomes",["less willing to accept worse moves","more willing to accept every worse move","identical to BFS","undecidable"],"A","Cooling reduces exploratory acceptance."),
("u4_heuristic","In A*, f(n) is commonly",["g(n)+h(n)","g(n)×h(n) only","h(n)−g(n)","vertex degree"],"A","A* combines known cost-so-far and estimated remaining cost."),
("u4_heuristic","In A*, g(n) represents",["cost from the start to n","estimated cost from n to goal","temperature","number of colours"],"A","g is the accumulated path cost."),
("u4_heuristic","In A*, h(n) represents",["estimated remaining cost to the goal","exact cost already paid","MST weight","recursion depth necessarily"],"A","h is the heuristic estimate."),
("u4_classic","In 0–1 knapsack, each item may be",["chosen at most once","split fractionally without limit","chosen only if weight zero","used only as a vertex"],"A","0–1 means take or do not take each whole item."),
("u4_classic","Graph colouring requires",["adjacent vertices to satisfy the different-colour constraint","all vertices the same colour","all weights 1","the graph to become a tree"],"A","Colour conflicts are defined on adjacent vertices."),
("u4_classic","Travelling salesman asks for",["a minimum-cost tour through all required vertices","an MST only","one shortest path between fixed vertices","a BFS tree"],"A","TSP optimises a tour, not a tree or one path."),
("u4_computability","Hilbert's program broadly sought",["a secure formal foundation for mathematics with consistency/completeness ambitions","Dijkstra","neural-network training","an MST"],"A","It motivated foundational questions in mathematics and computation."),
("u4_computability","A Turing machine is",["an abstract computation model with states, tape and transition rules","a laptop model","a sorting algorithm","an SVM"],"A","It is a mathematical model of computation."),
("u4_computability","The Halting Problem asks whether",["a program will halt on a given input","a graph has an MST","a queue is FIFO","an SVM has margin"],"A","That is the Halting Problem."),
("u4_computability","The Halting Problem is",["undecidable in general","NP-complete and therefore polynomial","a sort","solved by a one-second timeout"],"A","No decider can correctly halt on every instance."),
("u4_computability","An undecidable problem has",["no algorithm that correctly decides every input and always halts","only a slow known algorithm","an O(n²) lower bound","large inputs only"],"A","Undecidability is a hard computability limit."),
("u4_computability","The Church–Turing thesis connects effective computation with",["Turing-equivalent computation models","P=NP","optimal heuristics","AI consciousness"],"A","It states the intended equivalence of effective calculability and Turing-computability."),
("u4_ai","The Turing Test concerns whether",["a machine's conversational behaviour can be indistinguishable from a human's to an evaluator","MST optimality","NP reductions","queue signatures"],"A","It is a behavioural test of machine intelligence."),
("u4_ai","Weak AI usually means",["systems for specific intelligent tasks without a claim of general human-like understanding","uncomputable AI","low numerical accuracy","an MST"],"A","Weak AI is task-specific/narrow AI."),
("u4_ai","Strong AI is associated with the claim that machines could",["possess genuine general intelligence/understanding","only run BFS","never learn","be stacks"],"A","Strong AI makes the stronger claim of genuine mind-like understanding."),
("u4_ai","The Chinese Room questions whether",["successful symbol manipulation necessarily implies understanding","binary search is logarithmic","Prim is greedy","queues are FIFO"],"A","Searle separates syntactic symbol handling from semantic understanding."),
("u4_ml","Supervised learning uses",["labelled examples","no data","only unlabelled clusters","a Turing tape instead of data"],"A","Inputs are paired with target labels/outputs."),
("u4_ml","Overfitting means a model",["fits training data too specifically and generalises poorly","is too simple for even training data","has no parameters","uses BFS"],"A","Overfit models show poor generalisation despite strong training fit."),
("u4_ml","Underfitting means a model",["is too simple/insufficient to capture important patterns","memorises training data perfectly","uses a test set","has a margin"],"A","Underfit models perform poorly even on training patterns."),
("u4_ml","Why keep test data separate from training data?",["to estimate performance on unseen data","to reveal test answers during training","to guarantee zero error","to prove decidability"],"A","A held-out test set gives a cleaner generalisation estimate."),
("u4_ml","A standard SVM seeks a boundary that",["maximises the margin between classes","minimises graph vertices","passes the Turing Test","performs DFS"],"A","Maximum-margin separation is the core SVM idea."),
("u4_ml","Support vectors are",["training points that constrain the separating margin","all farthest points","Turing symbols","MST edges"],"A","Support vectors lie on/near the margin and determine the boundary."),
("u4_ml","A neural network is conceptually built from",["interconnected units with weighted inputs through layers","a FIFO queue only","one immutable edge","a proof by contradiction"],"A","Layered weighted units form the common neural-network abstraction."),
("u4_ethics","A model trained on historically biased decisions may",["learn and reproduce those biases","remove all bias automatically","become undecidable","guarantee equal outcomes"],"A","Training data can encode historical bias."),
("u4_ethics","Why can explainability matter in high-stakes ML?",["people may need to understand or challenge consequential decisions","it guarantees 100% accuracy","it makes O(1) models","it proves consciousness"],"A","Accountability and contestability can require explanations."),
("u4_ethics","High overall accuracy alone does not settle",["fairness, consent, accountability and appropriate use","whether accuracy is numeric","whether computers use electricity","FIFO"],"A","Technical accuracy is only one ethical consideration."),
]
for item in FACTS:
    q(*item)

TRACE_VALUES = [
[3,7,2],[5,1,9,4],[8,6,11],[11,4,12],[2,10,3,9],[14,1,6],[7,5,19],
[21,13,8],[4,16,12,2],[9,3,15],[1,2,3,4,5],[18,5,17],[6,20,2],[30,10,40],
[12,1,19,7],[23,4,5],[15,14,13],[27,6,18],[32,8,2,1],[17,29,3],
]
for i, values in enumerate(TRACE_VALUES):
    correct = values[-1]
    pool = list(dict.fromkeys([correct, values[0], min(values), max(values), correct+1]))
    while len(pool)<4: pool.append(max(pool)+1)
    rotated("u3_adt",f"An empty stack receives push({', '.join(map(str,values))}) in that order. What does top() return?",pool[:4],correct,"A stack returns the most recently pushed remaining item.",i)
for i, values in enumerate(TRACE_VALUES):
    correct = values[0]
    pool = list(dict.fromkeys([correct, values[-1], min(values), max(values), correct+2]))
    while len(pool)<4: pool.append(max(pool)+1)
    rotated("u3_adt",f"An empty queue receives {', '.join(map(str,values))} by enqueue in that order. What does front() return?",pool[:4],correct,"A queue exposes the earliest enqueued remaining item.",i+1)

for n in range(2,27):
    correct=n-1
    rotated("u3_graph",f"A connected undirected graph is a tree with {n} vertices. How many edges?",[correct,n,n+1,max(0,n-2)],correct,"Every n-vertex tree has n−1 edges.",n)
for n in range(3,23):
    correct=n*(n-1)//2
    rotated("u3_graph",f"How many edges are in a complete undirected graph with {n} vertices?",[correct,n*(n-1),n-1,n*n],correct,f"There is one edge per unordered pair: {n}({n}−1)/2={correct}.",n+1)

for n in range(4,29):
    correct=n*(n+1)//2
    rotated("u3_pseudocode",f"total←0; For i in {{1,…,{n}}}: total←total+i. What is total?",[correct,n*n,n*(n-1)//2,n+1],correct,f"The loop sums 1+…+{n}={correct}.",n)
for n in range(5,30):
    correct=(n+1)//2
    candidates=list(dict.fromkeys([correct,n//2,n,max(1,correct-1),correct+2]))[:4]
    while len(candidates)<4: candidates.append(max(candidates)+1)
    rotated("u3_pseudocode",f"A loop visits i=1,3,5,… while i≤{n}. How many iterations occur?",candidates,correct,f"There are {correct} odd positive integers up to {n}.",n+2)

for k in range(2,32):
    q("u4_complexity",f"An algorithm performs {k}n²+{k+3}n+7 primitive operations. Its Big-O time is",["O(1)","O(n)","O(n²)","O(2ⁿ)"],"C","The n² term dominates.")
for base in [2,3,4,5,6,8,10,12,16,20,24,32,50,64,100,128,256,512,1000,1024]:
    q("u4_complexity",f"x starts at 1 and is repeatedly multiplied by {base} until x≥n. The iteration count is",["O(1)","O(log n)","O(n)","O(n²)"],"B","Repeated multiplication reaches n in logarithmically many steps.")

MASTER = [
("2T(n/2)+n","O(n log n)"),("2T(n/2)+1","O(n)"),("T(n/2)+1","O(log n)"),
("4T(n/2)+n","O(n²)"),("4T(n/2)+n²","O(n² log n)"),("8T(n/2)+n²","O(n³)"),
("3T(n/3)+n","O(n log n)"),("9T(n/3)+n","O(n²)"),("9T(n/3)+n²","O(n² log n)"),
("T(n/3)+1","O(log n)"),("2T(n/4)+n","O(n)"),("4T(n/4)+n","O(n log n)"),
("16T(n/4)+n","O(n²)"),("16T(n/4)+n²","O(n² log n)"),
]
MASTER_OPTS=["O(log n)","O(n)","O(n log n)","O(n²)","O(n² log n)","O(n³)"]
for i,(rec,correct) in enumerate(MASTER):
    ds=[x for x in MASTER_OPTS if x!=correct]
    opts=[correct,ds[i%len(ds)],ds[(i+2)%len(ds)],ds[(i+4)%len(ds)]]
    opts=list(dict.fromkeys(opts))
    for x in MASTER_OPTS:
        if len(opts)==4: break
        if x not in opts: opts.append(x)
    rotated("u4_recurrence",f"What is the asymptotic solution of T(n)={rec}?",opts,correct,"Apply the Master Theorem / recurrence growth comparison.",i)

for n in [8,10,16,20,31,32,50,64,100,128,200,256,500,512,1000,1024,2048,4096,8192,10000]:
    correct=math.ceil(math.log2(n+1))
    vals=list(dict.fromkeys([correct,max(1,correct-1),correct+1,n]))
    while len(vals)<4: vals.append(correct+len(vals))
    rotated("u4_divide",f"About how many comparisons suffice in the worst case for binary search on {n} sorted items?",vals[:4],correct,f"ceil(log₂({n}+1))={correct}.",n)

for amount,coin in [(17,5),(23,6),(29,7),(31,8),(37,9),(41,10),(46,11),(52,12),(58,13),(63,14),(71,15),(79,16),(83,17),(91,18),(97,20),(103,21),(111,22),(119,25),(127,26),(137,30)]:
    correct=amount//coin+amount%coin
    vals=list(dict.fromkeys([correct,amount//coin,amount%coin,correct+1,correct+2]))[:4]
    while len(vals)<4: vals.append(max(vals)+1)
    rotated("u4_dp",f"Unlimited coins have values 1 and {coin}. What is the minimum number of coins to make {amount}?",vals,correct,f"Use {amount//coin} coin(s) of {coin} and {amount%coin} one(s): {correct} coins.",amount)

for capacity,chosen in [(10,12),(14,17),(18,21),(20,25),(25,29),(30,31),(34,40),(40,44),(45,51),(50,57),(60,63),(70,78),(80,91),(90,103)]:
    q("u4_backtracking",f"In 0–1 knapsack backtracking, chosen items already weigh {chosen} with capacity {capacity}. What should happen?",["prune this branch","add every remaining item","accept it as feasible","run PageRank"],"A","The partial solution already violates capacity, so descendants remain infeasible.")

SCENARIOS=[
("A courier needs the cheapest round trip through every listed suburb.","travelling salesman"),
("Conflicting exams must be assigned different timeslots.","graph colouring"),
("Choose indivisible projects under a budget to maximise benefit.","0–1 knapsack"),
("Neighbouring radio towers must receive different frequencies.","graph colouring"),
("Choose whole packages under a weight limit to maximise value.","0–1 knapsack"),
("Find the cheapest closed tour through all required depots.","travelling salesman"),
("Conflicting meetings must be assigned different rooms/time labels.","graph colouring"),
("Choose whole files for a size-limited cache to maximise utility.","0–1 knapsack"),
("Visit every required city once in a minimum-cost tour.","travelling salesman"),
("Assign colours to a map so adjacent regions differ.","graph colouring"),
("Select indivisible investments under a fixed capital limit.","0–1 knapsack"),
("Plan a minimum-distance Hamiltonian-style round trip through all stops.","travelling salesman"),
]
for i,(stem,correct) in enumerate(SCENARIOS):
    rotated("u4_classic",stem+" Which studied problem best models it?",["graph colouring","0–1 knapsack","travelling salesman","minimum spanning tree"],correct,"This scenario matches the defining constraint/objective.",i)

for i,(train,test) in enumerate([(99,58),(97,61),(96,60),(95,62),(94,59),(98,63),(92,57),(99,65),(93,55),(97,64),(96,52),(95,60),(98,66),(94,54),(97,59)]):
    rotated("u4_ml",f"A classifier gets {train}% on training data but {test}% on unseen test data. What is most strongly suggested?",["overfitting","underfitting","perfect generalisation","undecidability"],"overfitting","A large train–test gap is a classic overfitting warning.",i)
for i,acc in enumerate([51,54,57,60,62,64,66,68,70,72,73,74]):
    rotated("u4_ml",f"A simple model performs poorly on training data ({acc}%) and similarly on test data. What is most plausible?",["underfitting","overfitting","NP-completeness","a negative cycle"],"underfitting","Poor performance even on training data suggests underfitting.",i+1)

ETHICS=[
"A face-recognition system is trained mostly on one demographic group and performs worse on others.",
"A loan model uses postcode as a strong proxy for disadvantage.",
"A school uses an opaque risk score affecting opportunities with no appeal process.",
"A health app reuses sensitive training data for a new purpose without meaningful consent.",
"An automated welfare system has false positives that trigger costly investigations.",
"A company reports only overall accuracy despite much worse subgroup false-negative rates.",
"No party accepts responsibility when an automated decision harms a user.",
"A hiring system is retrained on past decisions reflecting discrimination.",
"A medical model is deployed on a population unlike its training population.",
"A predictive system gives high confidence but no way to contest harmful decisions.",
]
for i,stem in enumerate(ETHICS):
    correct="Investigate bias, affected groups, accountability and consequences."
    rotated("u4_ethics",stem+" What is the most appropriate response?",[correct,"Assume mathematics guarantees fairness.","Ignore subgroup behaviour if overall accuracy is high.","Automation removes human responsibility."],correct,"Responsible deployment requires examining bias, impact and accountability.",i)

EXTRA=[
("u3_design","Which method is most naturally suited to proving a recursive claim from smaller instances?",["induction","random testing","PageRank","hill climbing"],"induction","Induction mirrors the smaller-instance structure."),
("u3_design","Which method assumes the desired result is false and derives an impossibility?",["contradiction","BFS","greedy","simulation"],"contradiction","That is proof by contradiction."),
("u3_graph_alg","Which studied algorithm repeatedly relaxes every edge?",["Bellman–Ford","Prim","BFS","PageRank"],"Bellman–Ford","Bellman–Ford repeatedly relaxes all edges."),
("u3_graph_alg","Which studied algorithm grows a spanning tree using the cheapest crossing edge?",["Prim","Floyd–Warshall","DFS","PageRank"],"Prim","That is Prim's greedy rule."),
("u3_graph_alg","Which studied algorithm is most direct for all-pairs shortest paths?",["Floyd–Warshall","Prim","DFS","binary search"],"Floyd–Warshall","Floyd–Warshall computes all-pairs shortest paths."),
("u4_classes","Which question remains open?",["whether P=NP","whether P⊆NP","whether binary search is polynomial","whether Halting is undecidable"],"whether P=NP","P versus NP remains open."),
("u4_classes","A polynomial reduction A→B is useful for proving B hard when",["A is already known hard","B is trivial","the reduction is exponential","A has no inputs"],"A is already known hard","Hardness transfers from A to B through an efficient reduction."),
("u4_classes","A decision version of TSP asks whether",["a tour of cost at most K exists","the graph has a vertex","one edge is shortest","a queue is empty"],"a tour of cost at most K exists","A threshold turns optimisation into yes/no form."),
("u4_divide","Which algorithm explicitly merges sorted subarrays?",["mergesort","quicksort","Prim","PageRank"],"mergesort","Merging is mergesort's combine step."),
("u4_divide","Which algorithm usually partitions around a pivot?",["quicksort","mergesort","Bellman–Ford","BFS"],"quicksort","Pivot partitioning is quicksort's divide step."),
("u4_dp","What is the central DP efficiency idea?",["store/reuse subproblem results","randomly restart forever","enumerate all permutations twice","use only graphs"],"store/reuse subproblem results","Memoisation/tabulation prevents repeated work."),
("u4_backtracking","What distinguishes backtracking from blind exhaustive search?",["early pruning of impossible partial solutions","always O(n) time","no search tree","guaranteed approximation"],"early pruning of impossible partial solutions","Backtracking stops exploring invalid branches."),
("u4_heuristic","Which technique may accept a worse move early to escape local optima?",["simulated annealing","binary search","Floyd–Warshall","Prim"],"simulated annealing","Temperature-controlled worse moves aid exploration."),
("u4_heuristic","Which technique repeatedly chooses an improving neighbour and may get stuck locally?",["hill climbing","mergesort","Bellman–Ford","BFS"],"hill climbing","That is basic hill climbing."),
("u4_computability","Which is a hard computability limit rather than only a scaling problem?",["Halting Problem undecidability","O(n²) runtime","large constant factor","local optimum"],"Halting Problem undecidability","Undecidability means no general decider exists."),
("u4_computability","Undecidable and intractable differ because",["undecidable means no always-halting correct decider; intractable may still be computable","they are synonyms","intractable means O(n²)","undecidable means NP-complete"],"undecidable means no always-halting correct decider; intractable may still be computable","Computability and practical complexity are different limits."),
("u4_computability","A decider must",["halt on every input with the correct yes/no answer","only work on tested inputs","be polynomial","be a neural network"],"halt on every input with the correct yes/no answer","A decider must halt on all inputs."),
("u4_ai","A chatbot indistinguishable from a human to judges illustrates the",["Turing Test","Chinese Room","Prim test","Master Theorem"],"Turing Test","The Turing Test is behavioural indistinguishability in conversation."),
("u4_ai","A person follows Chinese symbol rules without understanding Chinese. This is the",["Chinese Room","Turing Test","PageRank model","Halting proof"],"Chinese Room","This is Searle's Chinese Room thought experiment."),
("u4_ai","A chess-only expert program is best described as",["weak AI","strong AI","undecidable AI","NP-complete AI"],"weak AI","It is narrow/task-specific intelligence."),
("u4_ai","The claim that a machine could genuinely understand generally is associated with",["strong AI","weak AI","BFS","SVM margin"],"strong AI","Strong AI makes a claim about genuine general intelligence."),
("u4_computability","A Turing-machine transition depends most directly on",["current state and symbol read","only wall-clock time","only graph degree","training accuracy"],"current state and symbol read","Transition rules use the current state and tape symbol."),
("u4_ai","Passing a Turing Test by itself",["gives behavioural evidence but does not settle every question about understanding","proves P=NP","proves zero error","solves Halting"],"gives behavioural evidence but does not settle every question about understanding","The test concerns behaviour, not a conclusive proof of inner understanding."),
("u4_ai","Searle's Chinese Room is mainly an argument about",["whether syntax alone guarantees semantic understanding","whether BFS is optimal","whether P contains NP","whether stacks are LIFO"],"whether syntax alone guarantees semantic understanding","The thought experiment separates symbol manipulation from understanding."),
]
for i,(topic,stem,opts,correct,explanation) in enumerate(EXTRA):
    rotated(topic,stem,opts,correct,explanation,i)

QUESTIONS=[]
for i,item in enumerate(_qs,1):
    item=dict(item); item["id"]=f"VCE{i:04d}"; QUESTIONS.append(item)
QUESTION_BY_ID={x["id"]:x for x in QUESTIONS}
TOPIC_LABELS={
"u3_adt":"U3 · ADTs & data modelling","u3_graph":"U3 · graph properties",
"u3_graph_alg":"U3 · graph algorithms","u3_design":"U3 · algorithm design & proof",
"u3_pseudocode":"U3 · pseudocode execution","u4_complexity":"U4 · Big-O & formal analysis",
"u4_recurrence":"U4 · recurrences & Master Theorem","u4_classes":"U4 · P / NP / NP-hard / NP-complete",
"u4_divide":"U4 · divide and conquer","u4_dp":"U4 · dynamic programming",
"u4_backtracking":"U4 · backtracking","u4_heuristic":"U4 · heuristics",
"u4_classic":"U4 · classic intractable problems","u4_computability":"U4 · computability & history",
"u4_ai":"U4 · AI philosophy","u4_ml":"U4 · machine learning","u4_ethics":"U4 · AI ethics",
}
