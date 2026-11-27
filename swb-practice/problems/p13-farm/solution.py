# 모범 답안: 버킷(제곱근 분할).
# 밭을 B칸씩 묶는다. 버킷마다
#   lazy[b] : 버킷 전체에 한꺼번에 더해진 값
#   bmax[b] : lazy를 빼고 본 arr 기준 최댓값
# 실제 높이는 arr[i] + lazy[i // B]이다.
# 구간이 버킷을 통째로 덮으면 lazy만 고치고(O(1)), 양 끝에 걸친 버킷만 칸을 직접 고친다(O(B)).
N = 0
B = 1
arr = []
lazy = []
bmax = []


def init(N_: int, mHeight: list) -> None:
    global N, B, arr, lazy, bmax
    N = N_
    B = max(1, int(N ** 0.5))
    arr = list(mHeight)
    nb = (N + B - 1) // B
    lazy = [0] * nb
    bmax = [max(arr[b * B:(b + 1) * B]) for b in range(nb)]


def add_part(l, r, v):
    """같은 버킷 안의 l..r 칸에 직접 v를 더하고 그 버킷의 최댓값을 다시 계산한다."""
    arr[l:r + 1] = [x + v for x in arr[l:r + 1]]
    b = l // B
    bmax[b] = max(arr[b * B:(b + 1) * B])


def grow(mL: int, mR: int, mV: int) -> None:
    bl, br = mL // B, mR // B
    if bl == br:
        add_part(mL, mR, mV)
        return
    add_part(mL, (bl + 1) * B - 1, mV)      # 왼쪽 끝 버킷 (일부)
    add_part(br * B, mR, mV)                # 오른쪽 끝 버킷 (일부)
    for b in range(bl + 1, br):             # 가운데 버킷은 통째로
        lazy[b] += mV


def cut(mIdx: int) -> int:
    b = mIdx // B
    h = arr[mIdx] + lazy[b]
    arr[mIdx] = -lazy[b]                    # 실제 높이가 0이 되도록
    bmax[b] = max(arr[b * B:(b + 1) * B])
    return h


def tallest(mL: int, mR: int) -> int:
    bl, br = mL // B, mR // B
    if bl == br:
        return max(arr[mL:mR + 1]) + lazy[bl]
    best = max(max(arr[mL:(bl + 1) * B]) + lazy[bl],
               max(arr[br * B:mR + 1]) + lazy[br])
    for b in range(bl + 1, br):
        if bmax[b] + lazy[b] > best:
            best = bmax[b] + lazy[b]
    return best
