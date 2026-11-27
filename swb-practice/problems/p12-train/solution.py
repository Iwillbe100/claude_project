# 모범 답안: 이중 연결 리스트.
# 순서를 리스트로 들고 있지 않고, 객차마다 바로 앞(prv)과 바로 뒤(nxt)만 dict에 저장한다.
# 넣기·빼기·옮기기가 모두 O(1), getCars는 O(mCnt)이다.
prv = {}
nxt = {}
count = 0


def init() -> None:
    global prv, nxt, count
    prv = {}
    nxt = {0: -1}    # 기관차 0번. 뒤에 아무것도 없으면 -1
    count = 0


def link_after(x, p):
    """x를 p 바로 뒤에 끼운다."""
    q = nxt[p]
    nxt[p] = x
    prv[x] = p
    nxt[x] = q
    if q != -1:
        prv[q] = x


def unlink(x):
    """x를 떼어 내고, 원래 x 뒤에 있던 번호를 반환한다."""
    p, q = prv[x], nxt[x]
    nxt[p] = q
    if q != -1:
        prv[q] = p
    return q


def addCar(mId: int, mPrevId: int) -> int:
    global count
    link_after(mId, mPrevId)
    count += 1
    return count


def removeCar(mId: int) -> int:
    global count
    q = unlink(mId)
    del prv[mId], nxt[mId]
    count -= 1
    return q


def moveCar(mId: int, mPrevId: int) -> int:
    if prv[mId] != mPrevId:          # 이미 그 자리이면 그대로 둔다
        unlink(mId)
        link_after(mId, mPrevId)
    return nxt[mId]


def getCars(mId: int, mCnt: int, mResult: list) -> int:
    k = 0
    x = mId
    while x != -1 and k < mCnt:
        mResult[k] = x
        k += 1
        x = nxt[x]
    return k
