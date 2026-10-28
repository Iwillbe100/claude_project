import sys
from solution import init, merge, isSame, groupSize, countGroups

input = sys.stdin.readline

CMD_MERGE = 1
CMD_SAME = 2
CMD_SIZE = 3
CMD_GROUPS = 4


def run():
    Q, N = map(int, input().split())
    init(N)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_MERGE:
            ret, ans = merge(p[1], p[2]), p[3]
        elif p[0] == CMD_SAME:
            ret, ans = isSame(p[1], p[2]), p[3]
        elif p[0] == CMD_SIZE:
            ret, ans = groupSize(p[1]), p[2]
        else:
            ret, ans = countGroups(), p[1]
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
