"""Locates the deletion cascade inside the height-7 minimum-node tree.

BUILD-TIME ONLY, like measure.py. Never referenced from the report prose.

The figure of the cascade is drawn by the recursive macro in
figures/fibtree.tex, which names its nodes f1, f2, ... in pre-order. To mark
the deleted leaf and the rotation sites in that picture, we need each one's
pre-order position. This prints them.

Run:  python cascade_sites.py
"""

from measure import (Node, fib_tree, number_inorder, height, bf, size,
                     rot_left, rot_right, update, check_avl, measured_height)

TARGET_HEIGHT = 7
VICTIM = 33


def preorder_index(root):
    """Pre-order numbering, matching the order the drawing macro visits nodes:
    the node itself, then the left subtree, then the right subtree."""
    idx = {}
    counter = [0]

    def walk(n):
        if n is None:
            return
        counter[0] += 1
        idx[id(n)] = counter[0]
        walk(n.left)
        walk(n.right)

    walk(root)
    return idx


class SiteLog:
    def __init__(self, idx):
        self.idx = idx
        self.sites = []

    def log(self, node, kind):
        self.sites.append((self.idx.get(id(node), "?"), kind, node.key))


def rebalance_logged(n, log):
    update(n)
    b = bf(n)
    if b > 1:
        if bf(n.left) >= 0:
            log.log(n, "LL")
            return rot_right(n)
        log.log(n, "LR")
        n.left = rot_left(n.left)
        return rot_right(n)
    if b < -1:
        if bf(n.right) <= 0:
            log.log(n, "RR")
            return rot_left(n)
        log.log(n, "RL")
        n.right = rot_right(n.right)
        return rot_left(n)
    return n


def delete_logged(n, key, log):
    if n is None:
        return None
    if key < n.key:
        n.left = delete_logged(n.left, key, log)
    elif key > n.key:
        n.right = delete_logged(n.right, key, log)
    else:
        if n.left is None:
            return n.right
        if n.right is None:
            return n.left
        s = n.right
        while s.left:
            s = s.left
        n.key = s.key
        n.right = delete_logged(n.right, s.key, log)
    return rebalance_logged(n, log)


def depth_of(root, key):
    d, cur = 0, root
    while cur is not None and cur.key != key:
        cur = cur.left if key < cur.key else cur.right
        d += 1
    return d


if __name__ == "__main__":
    t = fib_tree(TARGET_HEIGHT)
    n = number_inorder(t)
    idx = preorder_index(t)
    by_key = {}

    def collect(x):
        if x is None:
            return
        by_key[x.key] = idx[id(x)]
        collect(x.left)
        collect(x.right)

    collect(t)

    print("minimum tree of height %d: %d nodes, height %d"
          % (TARGET_HEIGHT, n, height(t)))
    print("victim leaf: key %d -> drawn node f%d, at depth %d"
          % (VICTIM, by_key[VICTIM], depth_of(t, VICTIM)))

    log = SiteLog(idx)
    t = delete_logged(t, VICTIM, log)
    assert check_avl(t), "the invariant did not survive the deletion"

    print("rebalance events: %d" % len(log.sites))
    for order, (pos, kind, key) in enumerate(log.sites, 1):
        print("  %d. drawn node f%-3d  case %s  (key %s)" % (order, pos, kind, key))
    print("after: %d nodes, height %d" % (size(t), measured_height(t)))
