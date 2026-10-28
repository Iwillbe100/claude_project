import sys
from solution import init, addDesk, minTime

input = sys.stdin.readline

CMD_ADD = 1
CMD_MIN = 2


def run():
    N, Q = map(int, input().split())
    mTime = list(map(int, input().split()))
    init(N, mTime)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            addDesk(p[1])
        else:
            if minTime(p[1]) != p[2]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
