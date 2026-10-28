import sys
from solution import init, update, query

input = sys.stdin.readline

CMD_UPDATE = 1
CMD_QUERY = 2


def run():
    N, Q = map(int, input().split())
    mValue = list(map(int, input().split()))
    init(N, mValue)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_UPDATE:
            update(p[1], p[2])
        else:
            if query(p[1], p[2]) != p[3]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
