import sys
from solution import init, add, removeDept, getTotal

input = sys.stdin.readline

CMD_ADD = 1
CMD_REMOVE = 2
CMD_TOTAL = 3


def run():
    Q, rootId, rootNum = map(int, input().split())
    init(rootId, rootNum)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            ret = add(p[1], p[2], p[3])
            ans = p[4]
        elif p[0] == CMD_REMOVE:
            ret = removeDept(p[1])
            ans = p[2]
        else:
            ret = getTotal(p[1])
            ans = p[2]
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
