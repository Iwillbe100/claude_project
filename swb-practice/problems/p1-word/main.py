import sys
from solution import init, add, removeWord, countPrefix

input = sys.stdin.readline

CMD_ADD = 1
CMD_REMOVE = 2
CMD_PREFIX = 3


def run():
    Q = int(input())
    init()
    okay = True
    for _ in range(Q):
        cmd, s, ans = input().split()
        cmd, ans = int(cmd), int(ans)
        if cmd == CMD_ADD:
            ret = add(s)
        elif cmd == CMD_REMOVE:
            ret = removeWord(s)
        else:
            ret = countPrefix(s)
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
