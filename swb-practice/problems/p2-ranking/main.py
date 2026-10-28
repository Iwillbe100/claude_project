import sys
from solution import init, update, removeUser, getTop

input = sys.stdin.readline

CMD_UPDATE = 1
CMD_REMOVE = 2
CMD_TOP = 3


def run():
    Q = int(input())
    init()
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_UPDATE:
            update(p[1], p[2])
        elif p[0] == CMD_REMOVE:
            if removeUser(p[1]) != p[2]:
                okay = False
        else:
            K, cnt = p[1], p[2]
            result = [0] * K
            ret = getTop(K, result)
            if ret != cnt or result[:cnt] != p[3:3 + cnt]:
                okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
