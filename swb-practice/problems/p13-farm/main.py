import sys
from solution import init, grow, cut, tallest

input = sys.stdin.readline

CMD_GROW = 1
CMD_CUT = 2
CMD_TALLEST = 3


def run():
    N, Q = map(int, input().split())
    mHeight = list(map(int, input().split()))
    init(N, mHeight)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_GROW:
            grow(p[1], p[2], p[3])
        elif p[0] == CMD_CUT:
            if cut(p[1]) != p[2]:
                okay = False
        else:
            if tallest(p[1], p[2]) != p[3]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
