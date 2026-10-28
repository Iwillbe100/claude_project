# 모범 답안: 힙 + 지연 삭제(lazy deletion)
# 점수가 바뀌거나 사용자가 삭제되면 힙에서 바로 지우지 않고, 꺼낼 때 버전을 비교해 무효한 항목을 버린다.
from heapq import heappush, heappop

score = {}
version = {}
heap = []
stamp = 0


def init() -> None:
    global score, version, heap, stamp
    score = {}
    version = {}
    heap = []
    stamp = 0


def update(mId: int, mScore: int) -> None:
    global stamp
    stamp += 1
    score[mId] = mScore
    version[mId] = stamp
    heappush(heap, (-mScore, mId, stamp))


def removeUser(mId: int) -> int:
    if mId not in score:
        return -1
    del version[mId]
    return score.pop(mId)


def getTop(K: int, mResult: list) -> int:
    taken = []
    while heap and len(taken) < K:
        item = heappop(heap)
        if version.get(item[1]) == item[2]:
            taken.append(item)
    for i, item in enumerate(taken):
        mResult[i] = item[1]
        heappush(heap, item)
    return len(taken)
