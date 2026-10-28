import sys
from solution import init, addRoad, shortest

input = sys.stdin.readline

CMD_ADD = 1
CMD_SHORTEST = 2


def run():
    N, K, Q = map(int, input().split())
    sCity, eCity, mTime = [], [], []
    for _ in range(K):
        s, e, t = map(int, input().split())
        sCity.append(s)
        eCity.append(e)
        mTime.append(t)
    init(N, K, sCity, eCity, mTime)

    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            addRoad(p[1], p[2], p[3])
        else:
            if shortest(p[1], p[2]) != p[3]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
