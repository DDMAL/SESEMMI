from collections import deque


class Node:
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


class Edge:
    def __init__(self, source: Node, target: Node, name: str):
        self.source = source
        self.target = target
        self.name = name

    def __str__(self):
        return f"{self.name}: {self.source} -> {self.target}"


class Graph:
    def __init__(self, nodes: set[Node], edges: set[Edge]):
        self.nodes = nodes
        self.edges = edges

    def get_edges_on_paths(self, source: Node, target: Node) -> set[Edge]:
        # Forward BFS: nodes reachable from source
        forward_reachable: set[Node] = set()
        queue: deque[Node] = deque([source])
        while queue:
            node = queue.popleft()
            if node in forward_reachable:
                continue
            forward_reachable.add(node)
            for edge in self.edges:
                if edge.source is node:
                    queue.append(edge.target)

        # Backward BFS: nodes that can reach target (traverse edges in reverse)
        backward_reachable: set[Node] = set()
        queue = deque([target])
        while queue:
            node = queue.popleft()
            if node in backward_reachable:
                continue
            backward_reachable.add(node)
            for edge in self.edges:
                if edge.target is node:
                    queue.append(edge.source)

        return {
            e
            for e in self.edges
            if e.source in forward_reachable and e.target in backward_reachable
        }
