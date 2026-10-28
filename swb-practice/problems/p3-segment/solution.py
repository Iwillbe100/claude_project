# 모범 답안: 최댓값/최솟값 세그먼트 트리 (bottom-up 방식)
size = 1
mx = []
mn = []


def init(N: int, mValue: list) -> None:
    global size, mx, mn
    size = 1
    while size < N:
        size *= 2
    mx = [-1] * (2 * size)
    mn = [1 << 31] * (2 * size)
    mx[size:size + N] = mValue
    mn[size:size + N] = mValue
    for i in range(size - 1, 0, -1):
        mx[i] = max(mx[2 * i], mx[2 * i + 1])
        mn[i] = min(mn[2 * i], mn[2 * i + 1])


def update(mIdx: int, mValue: int) -> None:
    i = mIdx + size
    mx[i] = mn[i] = mValue
    i >>= 1
    while i:
        mx[i] = max(mx[2 * i], mx[2 * i + 1])
        mn[i] = min(mn[2 * i], mn[2 * i + 1])
        i >>= 1


def query(mFrom: int, mTo: int) -> int:
    lo = mFrom + size
    hi = mTo + size + 1
    big, small = -1, 1 << 31
    while lo < hi:
        if lo & 1:
            if mx[lo] > big: big = mx[lo]
            if mn[lo] < small: small = mn[lo]
            lo += 1
        if hi & 1:
            hi -= 1
            if mx[hi] > big: big = mx[hi]
            if mn[hi] < small: small = mn[hi]
        lo >>= 1
        hi >>= 1
    return big - small
