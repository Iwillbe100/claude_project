# 모범 답안: 로봇은 id → [행, 열, 방향] 딕셔너리, 칸 점유는 2차원 배열로 동시에 관리한다.
DR = (-1, 0, 1, 0)  # 위, 오른쪽, 아래, 왼쪽 (방향 번호 0~3, 시계 방향 순서)
DC = (0, 1, 0, -1)

n = 0
wall = []
occ = []        # occ[r][c] = 그 칸에 있는 로봇 id (없으면 0)
robots = {}


def init(N: int, mMap: list) -> None:
    global n, wall, occ, robots
    n = N
    wall = [row[:] for row in mMap]
    occ = [[0] * n for _ in range(n)]
    robots = {}


def addRobot(mId: int, mR: int, mC: int, mDir: int) -> int:
    if mId in robots or wall[mR][mC] == 1 or occ[mR][mC] != 0:
        return 0
    robots[mId] = [mR, mC, mDir]
    occ[mR][mC] = mId
    return 1


def removeRobot(mId: int) -> int:
    if mId not in robots:
        return 0
    r, c, _ = robots.pop(mId)
    occ[r][c] = 0
    return 1


def rotate(mId: int, mK: int) -> int:
    robot = robots[mId]
    robot[2] = (robot[2] + mK) % 4   # 파이썬의 % 는 음수여도 0~3이 나온다
    return robot[2]


def move(mId: int, mSteps: int) -> int:
    robot = robots[mId]
    r, c, d = robot
    moved = 0
    for _ in range(mSteps):
        nr, nc = r + DR[d], c + DC[d]
        if not (0 <= nr < n and 0 <= nc < n) or wall[nr][nc] == 1 or occ[nr][nc] != 0:
            break
        occ[r][c] = 0
        occ[nr][nc] = mId
        r, c = nr, nc
        moved += 1
    robot[0], robot[1] = r, c
    return moved


def whoAt(mR: int, mC: int) -> int:
    return occ[mR][mC]
