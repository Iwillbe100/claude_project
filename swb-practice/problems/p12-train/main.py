import sys
from solution import init, addCar, removeCar, moveCar, getCars

input = sys.stdin.readline

CMD_ADD = 1
CMD_REMOVE = 2
CMD_MOVE = 3
CMD_GET = 4


def run():
    Q = int(input())
    init()
    okay = True
    for _ in range(Q):
        p = list(map(int, input().split()))
        if p[0] == CMD_ADD:
            ret, ans = addCar(p[1], p[2]), p[3]
        elif p[0] == CMD_REMOVE:
            ret, ans = removeCar(p[1]), p[2]
        elif p[0] == CMD_MOVE:
            ret, ans = moveCar(p[1], p[2]), p[3]
        else:
            cnt, k = p[2], p[3]
            result = [0] * cnt
            ret, ans = getCars(p[1], cnt, result), k
            if result[:k] != p[4:4 + k]:
                okay = False
        if ret != ans:
            okay = False
    return okay


if __name__ == "__main__":
    T, MARK = map(int, input().split())
    for tc in range(1, T + 1):
        score = MARK if run() else 0
        print(f"#{tc} {score}", flush=True)
