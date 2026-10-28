import sys
from solution import init, submit, done, waiting

input = sys.stdin.readline

CMD_SUBMIT = 1
CMD_DONE = 2
CMD_WAITING = 3


def run():
    N, Q = map(int, input().split())
    init(N)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_SUBMIT:
            ret, ans = submit(p[1], p[2], p[3]), p[4]
        elif p[0] == CMD_DONE:
            ret, ans = done(p[1]), p[2]
        else:
            ret, ans = waiting(p[1]), p[2]
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
