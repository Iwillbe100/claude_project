import sys
from solution import init, setLand, getArea, countIsland

input = sys.stdin.readline

CMD_SET = 1
CMD_AREA = 2
CMD_COUNT = 3


def run():
    N, Q = map(int, input().split())
    mMap = [list(map(int, input().split())) for _ in range(N)]
    init(N, mMap)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_SET:
            setLand(p[1], p[2])
        elif p[0] == CMD_AREA:
            if getArea(p[1], p[2]) != p[3]:
                okay = False
        else:
            if countIsland() != p[1]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
