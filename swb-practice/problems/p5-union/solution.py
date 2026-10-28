# 모범 답안: 유니온 파인드 (경로 압축 + 크기 기준 합치기)
parent = []
size = []
groups = 0


def init(N: int) -> None:
    global parent, size, groups
    parent = list(range(N + 1))
    size = [1] * (N + 1)
    groups = N


def find(x: int) -> int:
    root = x
    while parent[root] != root:
        root = parent[root]
    while parent[x] != root:  # 경로 압축
        parent[x], x = root, parent[x]
    return root


def merge(mA: int, mB: int) -> int:
    global groups
    ra, rb = find(mA), find(mB)
    if ra != rb:
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]
        groups -= 1
    return size[ra]


def isSame(mA: int, mB: int) -> int:
    return 1 if find(mA) == find(mB) else 0


def groupSize(mA: int) -> int:
    return size[find(mA)]


def countGroups() -> int:
    return groups
