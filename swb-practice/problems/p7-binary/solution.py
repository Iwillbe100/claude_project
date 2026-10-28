# 모범 답안: 답(시간)에 대한 이분 탐색 (파라메트릭 서치)
# 시간 T 동안 심사할 수 있는 사람 수 = sum(T // t) 이고, T가 커질수록 늘어나기만 한다.
desks = []


def init(N: int, mTime: list) -> None:
    desks.clear()
    desks.extend(mTime)


def addDesk(mTime: int) -> None:
    desks.append(mTime)


def minTime(M: int) -> int:
    lo, hi = 1, min(desks) * M  # 가장 빠른 심사대 하나만으로도 hi 안에 끝낼 수 있다
    while lo < hi:
        mid = (lo + hi) // 2
        if sum(mid // t for t in desks) >= M:
            hi = mid
        else:
            lo = mid + 1
    return lo
