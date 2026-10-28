# 모범 답안: 큐를 쓰는 BFS. 처음 도착한 거리가 곧 최단 거리이다.
from collections import deque

n = 0
grid = []


def init(N: int, mMap: list) -> None:
    global n, grid
    n = N
    grid = [row[:] for row in mMap]


def toggle(mR: int, mC: int) -> None:
    grid[mR][mC] ^= 1


def shortest(mSR: int, mSC: int, mER: int, mEC: int) -> int:
    if grid[mSR][mSC] == 1 or grid[mER][mEC] == 1:
        return -1
    dist = [[-1] * n for _ in range(n)]
    dist[mSR][mSC] = 0
    q = deque([(mSR, mSC)])
    while q:
        r, c = q.popleft()
        if r == mER and c == mEC:
            return dist[r][c]
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and dist[nr][nc] < 0:
                dist[nr][nc] = dist[r][c] + 1
                q.append((nr, nc))
    return -1
