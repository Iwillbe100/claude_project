import sys
from solution import init, toggle, shortest

input = sys.stdin.readline

CMD_TOGGLE = 1
CMD_SHORTEST = 2


def run():
    N, Q = map(int, input().split())
    mMap = [list(map(int, input().split())) for _ in range(N)]
    init(N, mMap)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_TOGGLE:
            toggle(p[1], p[2])
        else:
            if shortest(p[1], p[2], p[3], p[4]) != p[5]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
