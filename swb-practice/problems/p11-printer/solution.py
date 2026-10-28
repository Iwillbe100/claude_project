# 모범 답안: 이벤트 기반 시뮬레이션.
# 시간을 1씩 세지 않고, "작업이 끝나는 순간"만 힙으로 관리하며 필요한 시각까지 한꺼번에 처리한다.
from heapq import heappush, heappop
from collections import deque

busy = []        # (끝나는 시각, 프린터 번호): 일하는 중인 프린터
idle = []        # 놀고 있는 프린터 번호 (힙: 가장 작은 번호를 바로 꺼낸다)
queue = deque()  # 기다리는 작업의 페이지 수 (먼저 온 순서)
finished = 0


def init(N: int) -> None:
    global busy, idle, queue, finished
    busy = []
    idle = list(range(N))   # 오름차순 리스트는 그대로 힙이다
    queue = deque()
    finished = 0


def advance(t: int) -> None:
    """끝나는 시각이 t 이하인 작업을 시간 순서대로 모두 처리한다."""
    global finished
    while busy and busy[0][0] <= t:
        end, p = heappop(busy)      # 끝나는 시각이 같으면 번호가 작은 프린터가 먼저 나온다
        finished += 1
        if queue:
            heappush(busy, (end + queue.popleft(), p))   # 기다리던 작업이 바로 그 시각에 시작
        else:
            heappush(idle, p)


def submit(mTime: int, mJobId: int, mPages: int) -> int:
    advance(mTime)
    if idle:
        p = heappop(idle)
        heappush(busy, (mTime + mPages, p))
        return p
    queue.append(mPages)
    return -1


def done(mTime: int) -> int:
    advance(mTime)
    return finished


def waiting(mTime: int) -> int:
    advance(mTime)
    return len(queue)
