# 모범 답안: 펜윅 트리(BIT).
# tree는 1번부터 쓴다. 칸 i(0부터)는 펜윅 트리의 i+1번 자리이다.
#   put/take  : 한 칸에 더하기          O(log N)
#   count     : prefix(r+1) - prefix(l) O(log N)
#   find      : 큰 단계부터 내려가는 k번째 찾기 O(log N)
# take는 실제로 뺄 수 있는 양을 알아야 하므로 칸별 책 수 cnt를 따로 저장한다.
N = 0
LOG = 0
tree = []
cnt = []
total = 0


def init(N_: int) -> None:
    global N, LOG, tree, cnt, total
    N = N_
    tree = [0] * (N + 1)
    cnt = [0] * N
    total = 0
    LOG = 0
    while (1 << LOG) <= N:
        LOG += 1


def _add(i, v):
    i += 1
    while i <= N:
        tree[i] += v
        i += i & -i


def _prefix(i):          # 0번 ~ i-1번 칸의 합 (펜윅 기준 1..i)
    s = 0
    while i > 0:
        s += tree[i]
        i -= i & -i
    return s


def put(mIdx: int, mCnt: int) -> int:
    global total
    cnt[mIdx] += mCnt
    total += mCnt
    _add(mIdx, mCnt)
    return cnt[mIdx]


def take(mIdx: int, mCnt: int) -> int:
    global total
    d = min(mCnt, cnt[mIdx])
    if d:
        cnt[mIdx] -= d
        total -= d
        _add(mIdx, -d)
    return d


def count(mL: int, mR: int) -> int:
    return _prefix(mR + 1) - _prefix(mL)


def find(mK: int) -> int:
    if mK > total:
        return -1
    pos = 0
    k = mK
    step = 1 << LOG
    while step:
        nxt = pos + step
        if nxt <= N and tree[nxt] < k:
            pos = nxt
            k -= tree[nxt]
        step >>= 1
    return pos           # 펜윅 기준 pos+1번 = 0부터 센 칸 번호 pos
