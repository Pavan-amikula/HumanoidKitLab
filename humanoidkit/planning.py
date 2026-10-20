"""Metric grid A* with footprint inflation and four-connected motion."""
import heapq
import math


class NoPath(RuntimeError):
    pass


class GridPlanner:
    def __init__(self, rectangles, resolution=0.1, radius=0.22):
        self.rectangles = rectangles
        self.resolution = resolution
        self.radius = radius
        self.bounds = (-2.4, -1.7, 2.4, 1.7)

    def cell(self, point):
        return tuple(round(float(v) / self.resolution) for v in point[:2])

    def metric(self, cell):
        return tuple(v * self.resolution for v in cell)

    def free(self, point):
        x, y = point
        a, b, c, d = self.bounds
        if not (a + self.radius <= x <= c - self.radius and
                b + self.radius <= y <= d - self.radius):
            return False
        return not any(l - self.radius <= x <= r + self.radius and
                       t - self.radius <= y <= u + self.radius
                       for l, t, r, u in self.rectangles)

    def segment_free(self, a, b):
        n = max(2, math.ceil(math.dist(a, b) / (self.resolution / 4)))
        return all(self.free((a[0] + (b[0]-a[0])*i/n,
                              a[1] + (b[1]-a[1])*i/n)) for i in range(n+1))

    def plan(self, start, goal):
        s, g = self.cell(start), self.cell(goal)
        if not self.segment_free(start, self.metric(s)) or not self.segment_free(self.metric(g), goal):
            raise NoPath("Start or docking position is obstructed")
        queue, previous, costs = [(0, s)], {}, {s: 0}
        while queue:
            _, p = heapq.heappop(queue)
            if p == g:
                cells = [p]
                while p != s:
                    p = previous[p]
                    cells.append(p)
                points = [tuple(start[:2])] + [self.metric(c) for c in reversed(cells)] + [tuple(goal[:2])]
                return [p for i, p in enumerate(points) if i == 0 or p != points[i-1]]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (p[0]+dx, p[1]+dy)
                if not self.segment_free(self.metric(p), self.metric(q)):
                    continue
                cost = costs[p] + 1
                if cost < costs.get(q, float("inf")):
                    costs[q], previous[q] = cost, p
                    h = abs(q[0]-g[0]) + abs(q[1]-g[1])
                    heapq.heappush(queue, (cost+h, q))
        raise NoPath("No footprint-clear path to docking position")
