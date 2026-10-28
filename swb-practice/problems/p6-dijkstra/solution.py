# 모범 답안: 인접 리스트 + 우선순위 큐 다익스트라 (목적지를 꺼내는 순간 종료)
from heapq import heappush, heappop

adj = []


def init(N: int, K: int, sCity: list, eCity: list, mTime: list) -> None:
    global adj
    adj = [[] for _ in range(N)]
    for i in range(K):
        addRoad(sCity[i], eCity[i], mTime[i])


def addRoad(mS: int, mE: int, mTime: int) -> None:
    adj[mS].append((mE, mTime))
    adj[mE].append((mS, mTime))


def shortest(mS: int, mE: int) -> int:
    INF = float("inf")
    dist = [INF] * len(adj)
    dist[mS] = 0
    heap = [(0, mS)]
    while heap:
        d, u = heappop(heap)
        if u == mE:
            return d
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heappush(heap, (nd, v))
    return -1
