import sys
from solution import init, addRobot, removeRobot, rotate, move, whoAt

input = sys.stdin.readline

CMD_ADD = 1
CMD_REMOVE = 2
CMD_ROTATE = 3
CMD_MOVE = 4
CMD_WHO = 5


def run():
    N, Q = map(int, input().split())
    mMap = [list(map(int, input().split())) for _ in range(N)]
    init(N, mMap)
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            ret, ans = addRobot(p[1], p[2], p[3], p[4]), p[5]
        elif p[0] == CMD_REMOVE:
            ret, ans = removeRobot(p[1]), p[2]
        elif p[0] == CMD_ROTATE:
            ret, ans = rotate(p[1], p[2]), p[3]
        elif p[0] == CMD_MOVE:
            ret, ans = move(p[1], p[2]), p[3]
        else:
            ret, ans = whoAt(p[1], p[2]), p[3]
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
