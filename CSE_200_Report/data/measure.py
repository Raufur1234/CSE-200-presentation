"""Generates every measured number and every plot table used by the report.

BUILD-TIME ONLY. This file must never be referred to from the report prose --
not by name, not by implication. See AGENTS.md, hard rule 1.

Emits, next to this file:
    nh_table.dat        minimum node counts N(h) against the perfect tree
    height_vs_n.dat     measured AVL height against the analytic bounds
    search_cost.dat     average successful-search comparisons, AVL vs plain BST
    rotations.dat       rebalancing work per insertion and per deletion
    summary.txt         scalar facts quoted in the prose

Height convention: h counts edges. A single node has height 0, the empty tree
has height -1. Under this convention N(h) = F(h+3) - 1.

Run:  python measure.py
"""

import math
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20250919

PHI = (1.0 + math.sqrt(5.0)) / 2.0
C_UPPER = 1.0 / math.log2(PHI)                      # 1.4404...

# The additive constant depends on the height convention, and getting it wrong
# shifts every bound by one level. Counting height in EDGES gives N(h) =
# F(h+3)-1 and the constant below. Counting height in levels instead, so that a
# single node has height 1, gives N(h) = F(h+2)-1 and -2 in place of the -3.
# We count edges. See AGENTS.md.
B_UPPER = (C_UPPER / 2.0) * math.log2(5.0) - 3.0    # -1.3277...


# --------------------------------------------------------------- AVL tree

class Node:
    __slots__ = ("key", "left", "right", "h")

    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None
        self.h = 0


def height(n):
    return -1 if n is None else n.h


def update(n):
    n.h = 1 + max(height(n.left), height(n.right))


def bf(n):
    return height(n.left) - height(n.right)


def size(n):
    return 0 if n is None else 1 + size(n.left) + size(n.right)


class Counter:
    """Counts rebalancing work.

    events    -- rebalance events; a double rotation is one event
    singles   -- single rotations; a double rotation counts as two
    """

    def __init__(self):
        self.events = 0
        self.singles = 0

    def log(self, kind):
        self.events += 1
        self.singles += 2 if kind in ("LR", "RL") else 1


def rot_right(y):
    x = y.left
    y.left = x.right
    x.right = y
    update(y)
    update(x)
    return x


def rot_left(x):
    y = x.right
    x.right = y.left
    y.left = x
    update(x)
    update(y)
    return y


def rebalance(n, c):
    update(n)
    b = bf(n)
    if b > 1:
        if bf(n.left) >= 0:
            c.log("LL")
            return rot_right(n)
        c.log("LR")
        n.left = rot_left(n.left)
        return rot_right(n)
    if b < -1:
        if bf(n.right) <= 0:
            c.log("RR")
            return rot_left(n)
        c.log("RL")
        n.right = rot_right(n.right)
        return rot_left(n)
    return n


def avl_insert(n, key, c):
    if n is None:
        return Node(key)
    if key < n.key:
        n.left = avl_insert(n.left, key, c)
    elif key > n.key:
        n.right = avl_insert(n.right, key, c)
    else:
        return n
    return rebalance(n, c)


def avl_delete(n, key, c):
    if n is None:
        return None
    if key < n.key:
        n.left = avl_delete(n.left, key, c)
    elif key > n.key:
        n.right = avl_delete(n.right, key, c)
    else:
        if n.left is None:
            return n.right
        if n.right is None:
            return n.left
        s = n.right
        while s.left:
            s = s.left
        n.key = s.key
        n.right = avl_delete(n.right, s.key, c)
    return rebalance(n, c)


def check_avl(n):
    if n is None:
        return True
    return abs(bf(n)) <= 1 and check_avl(n.left) and check_avl(n.right)


def depth_sum(root):
    """Sum of node depths, root at depth 0. Iterative: the plain BST built
    from sorted keys is a path, and recursion would overflow on it."""
    total = 0
    stack = [(root, 0)]
    while stack:
        n, d = stack.pop()
        if n is None:
            continue
        total += d
        stack.append((n.left, d + 1))
        stack.append((n.right, d + 1))
    return total


def measured_height(root):
    best = -1
    stack = [(root, 0)]
    while stack:
        n, d = stack.pop()
        if n is None:
            continue
        if d > best:
            best = d
        stack.append((n.left, d + 1))
        stack.append((n.right, d + 1))
    return best


# ------------------------------------------------------- plain (unbalanced)

def bst_insert_all(keys):
    """Iterative, so a degenerate path does not exhaust the Python stack."""
    root = None
    for k in keys:
        if root is None:
            root = Node(k)
            continue
        cur = root
        while True:
            if k < cur.key:
                if cur.left is None:
                    cur.left = Node(k)
                    break
                cur = cur.left
            elif k > cur.key:
                if cur.right is None:
                    cur.right = Node(k)
                    break
                cur = cur.right
            else:
                break
    return root


def avl_build(keys):
    root = None
    c = Counter()
    for k in keys:
        root = avl_insert(root, k, c)
    return root, c


# ------------------------------------------------------- minimum-node trees

def min_nodes(hmax):
    """N(h) = N(h-1) + N(h-2) + 1, with N(0) = 1 and N(1) = 2."""
    N = [1, 2]
    for h in range(2, hmax + 1):
        N.append(N[h - 1] + N[h - 2] + 1)
    return N[:hmax + 1]


def fibs(k):
    F = [0, 1]
    while len(F) <= k:
        F.append(F[-1] + F[-2])
    return F


def fib_tree(h):
    """Minimum-node AVL tree of height h."""
    if h < 0:
        return None
    if h == 0:
        return Node(None)
    n = Node(None)
    n.left = fib_tree(h - 1)
    n.right = fib_tree(h - 2)
    update(n)
    return n


def number_inorder(root):
    k = [0]
    stack, cur = [], root
    while stack or cur:
        while cur:
            stack.append(cur)
            cur = cur.left
        cur = stack.pop()
        k[0] += 1
        cur.key = k[0]
        cur = cur.right
    return k[0]


def leaves(root):
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        if n.left is None and n.right is None:
            out.append(n.key)
        stack.append(n.left)
        stack.append(n.right)
    return out


# --------------------------------------------------------------- emitters

def write_dat(name, header, rows, fmt):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# " + name + "\n")
        f.write("# generated by measure.py -- do not hand-edit\n")
        f.write(" ".join(header) + "\n")
        for r in rows:
            f.write(fmt.format(*r) + "\n")
    print("wrote", name, "(%d rows)" % len(rows))


def emit_nh_table():
    hmax = 15
    N = min_nodes(hmax)
    F = fibs(hmax + 4)
    rows = []
    for h in range(hmax + 1):
        perfect = 2 ** (h + 1) - 1
        assert N[h] == F[h + 3] - 1, "identity N(h) = F(h+3) - 1 failed at h=%d" % h
        if h <= 12:
            assert size(fib_tree(h)) == N[h], "constructed tree size differs at h=%d" % h
        rows.append((h, N[h], perfect, 100.0 * N[h] / perfect))
    write_dat("nh_table.dat", ["h", "Nh", "perfect", "fillpct"], rows,
              "{0} {1} {2} {3:.2f}")
    return N


def emit_height_vs_n():
    rng = random.Random(SEED)
    sizes = [10, 30, 100, 300, 1000, 3000, 10 ** 4, 3 * 10 ** 4,
             10 ** 5, 3 * 10 ** 5, 10 ** 6]
    rows = []
    for n in sizes:
        trials = 20 if n <= 3000 else (5 if n <= 10 ** 5 else 1)
        hs = []
        for _ in range(trials):
            keys = list(range(n))
            rng.shuffle(keys)
            root, _ = avl_build(keys)
            hs.append(measured_height(root))
        mean_h = statistics.fmean(hs)
        lower = math.log2(n + 1)
        upper = C_UPPER * math.log2(n + 2) + B_UPPER
        rows.append((n, mean_h, max(hs), lower, upper))
        print("  n=%-8d h=%.2f (max %d)  bounds [%.2f, %.2f]"
              % (n, mean_h, max(hs), lower, upper))
    write_dat("height_vs_n.dat",
              ["n", "meanh", "maxh", "lower", "upper"], rows,
              "{0} {1:.3f} {2} {3:.3f} {4:.3f}")
    return rows


def emit_search_cost():
    """Average comparisons for a successful search, which is one more than the
    mean node depth. The plain BST on sorted keys is quadratic to build, so the
    sorted series stops where it stops being cheap."""
    rng = random.Random(SEED + 1)
    sizes = [100, 300, 1000, 3000, 10 ** 4]
    rows = []
    for n in sizes:
        trials = 10 if n <= 3000 else 3

        avl_rand, bst_rand = [], []
        for _ in range(trials):
            keys = list(range(n))
            rng.shuffle(keys)
            root, _ = avl_build(keys)
            avl_rand.append(depth_sum(root) / n + 1.0)
            broot = bst_insert_all(keys)
            bst_rand.append(depth_sum(broot) / n + 1.0)

        ordered = list(range(n))
        aroot, _ = avl_build(ordered)
        avl_sorted = depth_sum(aroot) / n + 1.0
        broot = bst_insert_all(ordered)
        bst_sorted = depth_sum(broot) / n + 1.0

        rows.append((n, statistics.fmean(avl_rand), statistics.fmean(bst_rand),
                     avl_sorted, bst_sorted))
        print("  n=%-6d AVL rnd %.2f | BST rnd %.2f | AVL srt %.2f | BST srt %.1f"
              % (n, rows[-1][1], rows[-1][2], avl_sorted, bst_sorted))
    write_dat("search_cost.dat",
              ["n", "avlrand", "bstrand", "avlsorted", "bstsorted"], rows,
              "{0} {1:.3f} {2:.3f} {3:.3f} {4:.3f}")
    return rows


def emit_rotations():
    """Rebalancing work per operation. Build by random insertion, then delete
    every key in a fresh random order, counting each phase separately."""
    rng = random.Random(SEED + 2)
    sizes = [100, 300, 1000, 3000, 10 ** 4, 3 * 10 ** 4, 10 ** 5, 3 * 10 ** 5]
    rows = []
    for n in sizes:
        trials = 10 if n <= 3000 else (3 if n <= 10 ** 5 else 1)
        ins_ev, ins_si, del_ev, del_si = [], [], [], []
        for _ in range(trials):
            keys = list(range(n))
            rng.shuffle(keys)
            root, c = avl_build(keys)
            ins_ev.append(c.events / n)
            ins_si.append(c.singles / n)

            order = list(range(n))
            rng.shuffle(order)
            d = Counter()
            for k in order:
                root = avl_delete(root, k, d)
            assert root is None, "tree not empty after deleting every key"
            del_ev.append(d.events / n)
            del_si.append(d.singles / n)
        rows.append((n, statistics.fmean(ins_ev), statistics.fmean(ins_si),
                     statistics.fmean(del_ev), statistics.fmean(del_si)))
        print("  n=%-7d insert %.4f ev / %.4f rot | delete %.4f ev / %.4f rot"
              % (n, rows[-1][1], rows[-1][2], rows[-1][3], rows[-1][4]))
    write_dat("rotations.dat",
              ["n", "insev", "insrot", "delev", "delrot"], rows,
              "{0} {1:.4f} {2:.4f} {3:.4f} {4:.4f}")
    return rows


def emit_summary(N, hrows, srows, rrows):
    lines = []
    add = lines.append

    add("Scalar facts quoted in the report prose.")
    add("")
    add("golden ratio phi                 = %.6f" % PHI)
    add("c = 1 / log2(phi)                = %.6f" % C_UPPER)
    add("b = (c/2) log2(5) - 3            = %.6f" % B_UPPER)
    add("")

    # the height-7 minimum tree and its cascade
    t = fib_tree(7)
    n7 = number_inorder(t)
    add("minimum tree of height 7: %d nodes (perfect would be %d, %.1f%% full)"
        % (n7, 2 ** 8 - 1, 100.0 * n7 / (2 ** 8 - 1)))

    best = (-1, -1, None)
    for k in sorted(leaves(fib_tree_numbered(7))):
        t = fib_tree_numbered(7)
        c = Counter()
        t = avl_delete(t, k, c)
        assert check_avl(t), "deleting key %d broke the invariant" % k
        if (c.events, c.singles) > (best[0], best[1]):
            best = (c.events, c.singles, k, measured_height(t), size(t))
    add("worst leaf deletion: key %d -> %d rebalance events, %d single rotations"
        % (best[2], best[0], best[1]))
    add("                     nodes %d -> %d, height 7 -> %d"
        % (n7, best[4], best[3]))
    add("")

    # the bound at one million
    n = 10 ** 6
    upper = C_UPPER * math.log2(n + 2) + B_UPPER
    add("at n = 1,000,000:")
    add("  perfect-tree height (floor log2 n) = %d" % math.floor(math.log2(n)))
    add("  analytic upper bound               = %.3f  -> at most %d"
        % (upper, math.floor(upper)))
    add("  measured mean height               = %.1f" % hrows[-1][1])
    add("  largest h whose minimum tree fits  = %d"
        % (len([x for x in min_nodes(40) if x <= n]) - 1))
    add("")

    add("search comparisons at n = %d:" % srows[-1][0])
    add("  AVL, random keys   %.2f" % srows[-1][1])
    add("  BST, random keys   %.2f" % srows[-1][2])
    add("  AVL, sorted keys   %.2f" % srows[-1][3])
    add("  BST, sorted keys   %.1f" % srows[-1][4])
    add("  ratio BST/AVL on sorted keys = %.0fx" % (srows[-1][4] / srows[-1][3]))
    add("")

    add("rebalancing per operation, largest measured size (n = %d):" % rrows[-1][0])
    add("  insertion  %.4f events, %.4f single rotations" % (rrows[-1][1], rrows[-1][2]))
    add("  deletion   %.4f events, %.4f single rotations" % (rrows[-1][3], rrows[-1][4]))
    add("")
    add("insertion events per insert across all sizes: "
        + ", ".join("%.3f" % r[1] for r in rrows))
    add("deletion  events per delete across all sizes: "
        + ", ".join("%.3f" % r[3] for r in rrows))

    path = os.path.join(HERE, "summary.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def fib_tree_numbered(h):
    t = fib_tree(h)
    number_inorder(t)
    return t


if __name__ == "__main__":
    print("== minimum node counts ==")
    N = emit_nh_table()
    print("== height against n ==")
    hrows = emit_height_vs_n()
    print("== search cost ==")
    srows = emit_search_cost()
    print("== rebalancing work ==")
    rrows = emit_rotations()
    print("== summary ==")
    emit_summary(N, hrows, srows, rrows)
