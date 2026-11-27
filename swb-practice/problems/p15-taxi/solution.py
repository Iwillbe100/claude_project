# 모범 답안: 공간 분할 (격자 버킷).
# 지도를 한 변이 L인 칸으로 나눈다. 택시 (x, y)는 칸 (x // L, y // L)에 들어간다.
# 거리 L 이내의 택시는 질의 지점의 칸과 둘레 8칸(모두 9칸) 안에만 있다.
#   pos[id]        : 대기 중인 택시의 위치
#   cell[칸 번호]  : 그 칸에 있는 택시 ID의 set
# 칸 번호는 튜플 대신 정수 하나(cx * W + cy)로 만들어 dict를 빠르게 쓴다.
L = 1
W = 1
pos = {}
cell = {}


def init(N: int, L_: int) -> None:
    global L, W, pos, cell
    L = L_
    W = N // L + 3          # 칸 번호 cy의 범위(-1 ~ N//L + 1)보다 크게
    pos = {}
    cell = {}


def _key(x, y):
    return (x // L) * W + (y // L)


def addTaxi(mId: int, mX: int, mY: int) -> None:
    pos[mId] = (mX, mY)
    k = _key(mX, mY)
    s = cell.get(k)
    if s is None:
        s = cell[k] = set()
    s.add(mId)


def _remove(mId):
    x, y = pos.pop(mId)
    cell[_key(x, y)].discard(mId)


def moveTaxi(mId: int, mX: int, mY: int) -> None:
    _remove(mId)
    addTaxi(mId, mX, mY)


def _near(mX, mY):
    """9칸 안의 택시 중 거리 L 이내인 (거리, id)를 모두 만든다."""
    cx, cy = mX // L, mY // L
    for gx in range(cx - 1, cx + 2):
        base = gx * W
        for gy in range(cy - 1, cy + 2):
            s = cell.get(base + gy)
            if not s:
                continue
            for i in s:
                px, py = pos[i]
                d = abs(px - mX) + abs(py - mY)
                if d <= L:
                    yield d, i


def callTaxi(mX: int, mY: int) -> int:
    best = min(_near(mX, mY), default=None)   # (거리, id) 튜플 비교로 동점 처리
    if best is None:
        return -1
    _remove(best[1])                          # 반복이 끝난 뒤에 지운다
    return best[1]


def countTaxi(mX: int, mY: int) -> int:
    return sum(1 for _ in _near(mX, mY))
