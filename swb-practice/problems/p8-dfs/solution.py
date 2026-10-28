# 모범 답안: 재귀 DFS로 연결된 땅을 센다.
import sys

sys.setrecursionlimit(10000)  # 뱀처럼 길게 이어진 섬은 재귀 깊이가 1000을 넘는다

DR = (-1, 1, 0, 0)
DC = (0, 0, -1, 1)

n = 0
grid = []


def init(N: int, mMap: list) -> None:
    global n, grid
    n = N
    grid = [row[:] for row in mMap]


def setLand(mR: int, mC: int) -> None:
    grid[mR][mC] = 1


def dfs(r: int, c: int, seen: list) -> int:
    seen[r][c] = True
    area = 1
    for d in range(4):
        nr, nc = r + DR[d], c + DC[d]
        if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 1 and not seen[nr][nc]:
            area += dfs(nr, nc, seen)
    return area


def getArea(mR: int, mC: int) -> int:
    if grid[mR][mC] == 0:
        return 0
    return dfs(mR, mC, [[False] * n for _ in range(n)])


def countIsland() -> int:
    seen = [[False] * n for _ in range(n)]
    count = 0
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 1 and not seen[r][c]:
                dfs(r, c, seen)
                count += 1
    return count
