# 모범 답안: 부서 ID → 부모 / 하위 합계를 딕셔너리로 관리한다.
# 트리의 깊이가 100 이하이므로, 추가·삭제할 때 조상들을 따라 올라가며 합계를 갱신한다.
# 삭제된 부서는 removed 표시만 하고, 조상 중에 삭제된 부서가 있으면 그 부서도 없는 것으로 본다.

parent = {}
total = {}
removed = set()


def init(mId: int, mNum: int) -> None:
    global parent, total, removed
    parent = {mId: 0}
    total = {mId: mNum}
    removed = set()


def alive(mId: int) -> bool:
    while mId:
        if mId not in parent or mId in removed:
            return False
        mId = parent[mId]
    return True


def add(mId: int, mNum: int, mParent: int) -> int:
    if not alive(mParent):
        return -1
    parent[mId] = mParent
    total[mId] = mNum
    cur = mParent
    while cur:
        total[cur] += mNum
        cur = parent[cur]
    return total[mParent]


def removeDept(mId: int) -> int:
    if not alive(mId):
        return -1
    removed.add(mId)
    amount = total[mId]
    cur = parent[mId]
    while cur:
        total[cur] -= amount
        cur = parent[cur]
    return amount


def getTotal(mId: int) -> int:
    if not alive(mId):
        return -1
    return total[mId]
