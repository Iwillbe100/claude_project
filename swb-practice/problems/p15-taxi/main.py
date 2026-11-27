import sys
from solution import init, addTaxi, moveTaxi, callTaxi, countTaxi

input = sys.stdin.readline

CMD_ADD = 1
CMD_MOVE = 2
CMD_CALL = 3
CMD_COUNT = 4


def run():
    N, L, Q = map(int, input().split())
    init(N, L)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            addTaxi(p[1], p[2], p[3])
        elif p[0] == CMD_MOVE:
            moveTaxi(p[1], p[2], p[3])
        elif p[0] == CMD_CALL:
            if callTaxi(p[1], p[2]) != p[3]:
                okay = False
        else:
            if countTaxi(p[1], p[2]) != p[3]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
