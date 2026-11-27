import sys
from solution import init, put, take, count, find

input = sys.stdin.readline

CMD_PUT = 1
CMD_TAKE = 2
CMD_COUNT = 3
CMD_FIND = 4


def run():
    N, Q = map(int, input().split())
    init(N)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_PUT:
            ret, ans = put(p[1], p[2]), p[3]
        elif p[0] == CMD_TAKE:
            ret, ans = take(p[1], p[2]), p[3]
        elif p[0] == CMD_COUNT:
            ret, ans = count(p[1], p[2]), p[3]
        else:
            ret, ans = find(p[1]), p[2]
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
