"""테스트 데이터 생성기.

각 문제의 입력 파일에 정답을 함께 기록한다. (main.py가 반환값과 비교해 점수를 매긴다)
    python tools/gen.py            # 모든 문제 생성
    python tools/gen.py p2-ranking # 특정 문제만 생성
"""
import os
import random
import sys
from heapq import heappush, heappop

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = 100


def write(pid, name, cases):
    d = os.path.join(ROOT, "problems", pid, "tests")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", newline="\n") as f:
        f.write(f"{len(cases)} {MARK}\n")
        for lines in cases:
            f.write("\n".join(lines))
            f.write("\n")


# ---------------------------------------------------------------- p1 단어 사전
def p1_case(rng, Q, alpha, maxlen, pool_size):
    pool = ["".join(rng.choice(alpha) for _ in range(rng.randint(1, maxlen)))
            for _ in range(pool_size)]
    cnt, pc = {}, {}
    out = [str(Q)]
    for _ in range(Q):
        r = rng.random()
        w = rng.choice(pool)
        if r < 0.5:
            cnt[w] = cnt.get(w, 0) + 1
            for i in range(1, len(w) + 1):
                pc[w[:i]] = pc.get(w[:i], 0) + 1
            out.append(f"1 {w} {cnt[w]}")
        elif r < 0.7:
            if cnt.get(w, 0) == 0:
                ans = -1
            else:
                cnt[w] -= 1
                for i in range(1, len(w) + 1):
                    pc[w[:i]] -= 1
                ans = cnt[w]
            out.append(f"2 {w} {ans}")
        else:
            p = w[:rng.randint(1, len(w))]
            out.append(f"3 {p} {pc.get(p, 0)}")
    return out


def gen_p1(rng):
    write("p1-word", "sample.txt", [
        p1_case(rng, 10, "ab", 3, 6),
        p1_case(rng, 20, "abc", 4, 15),
        p1_case(rng, 30, "abcd", 5, 30),
    ])
    cases = []
    for i in range(10):
        Q = [500, 2000, 5000, 10000, 20000, 30000, 30000, 30000, 30000, 30000][i]
        alpha = "abcdefghijklmnopqrstuvwxyz"[: rng.choice([3, 5, 10, 26])]
        cases.append(p1_case(rng, Q, alpha, 10, rng.choice([50, 500, 3000, 10000])))
    write("p1-word", "test.txt", cases)


# ---------------------------------------------------------------- p2 실시간 랭킹
def p2_case(rng, Q, id_max, score_max):
    score, ver, heap = {}, {}, []
    stamp = 0
    out = [str(Q)]
    for _ in range(Q):
        r = rng.random()
        if r < 0.6 or not score:
            stamp += 1
            uid = rng.randint(1, id_max)
            s = rng.randint(0, score_max)
            score[uid] = s
            ver[uid] = stamp
            heappush(heap, (-s, uid, stamp))
            out.append(f"1 {uid} {s}")
        elif r < 0.7:
            if rng.random() < 0.8:
                uid = rng.choice(list(score)) if len(score) < 2000 else next(iter(score))
            else:
                uid = rng.randint(1, id_max)
            ans = score.pop(uid, -1)
            ver.pop(uid, None)
            out.append(f"2 {uid} {ans}")
        else:
            K = rng.randint(1, 10)
            taken = []
            while heap and len(taken) < K:
                it = heappop(heap)
                if ver.get(it[1]) == it[2]:
                    taken.append(it)
            for it in taken:
                heappush(heap, it)
            ids = " ".join(str(it[1]) for it in taken)
            out.append(f"3 {K} {len(taken)} {ids}".rstrip())
    return out


def gen_p2(rng):
    write("p2-ranking", "sample.txt", [
        p2_case(rng, 10, 5, 10),
        p2_case(rng, 20, 10, 5),
        p2_case(rng, 40, 30, 100),
    ])
    cases = []
    for i in range(10):
        Q = [1000, 5000, 10000, 20000, 50000, 50000, 50000, 50000, 50000, 50000][i]
        id_max = [100, 1000, 100000][i % 3]
        score_max = [10, 1000, 1000000][(i // 3) % 3]
        cases.append(p2_case(rng, Q, id_max, score_max))
    write("p2-ranking", "test.txt", cases)


# ---------------------------------------------------------------- p3 센서 편차
def p3_case(rng, N, Q, vmax):
    vals = [rng.randint(0, vmax) for _ in range(N)]
    size = 1
    while size < N:
        size *= 2
    mx = [-1] * (2 * size)
    mn = [1 << 31] * (2 * size)
    mx[size:size + N] = vals
    mn[size:size + N] = vals
    for i in range(size - 1, 0, -1):
        mx[i] = max(mx[2 * i], mx[2 * i + 1])
        mn[i] = min(mn[2 * i], mn[2 * i + 1])

    out = [f"{N} {Q}", " ".join(map(str, vals))]
    for _ in range(Q):
        if rng.random() < 0.5:
            idx, v = rng.randrange(N), rng.randint(0, vmax)
            i = idx + size
            mx[i] = mn[i] = v
            i >>= 1
            while i:
                mx[i] = max(mx[2 * i], mx[2 * i + 1])
                mn[i] = min(mn[2 * i], mn[2 * i + 1])
                i >>= 1
            out.append(f"1 {idx} {v}")
        else:
            a, b = rng.randrange(N), rng.randrange(N)
            if rng.random() < 0.3:  # 짧은 구간도 섞는다
                b = min(N - 1, a + rng.randint(0, 10))
            l, r = min(a, b), max(a, b)
            lo, hi = l + size, r + size + 1
            big, small = -1, 1 << 31
            while lo < hi:
                if lo & 1:
                    big, small = max(big, mx[lo]), min(small, mn[lo])
                    lo += 1
                if hi & 1:
                    hi -= 1
                    big, small = max(big, mx[hi]), min(small, mn[hi])
                lo >>= 1
                hi >>= 1
            out.append(f"2 {l} {r} {big - small}")
    return out


def gen_p3(rng):
    write("p3-segment", "sample.txt", [
        p3_case(rng, 5, 6, 10),
        p3_case(rng, 10, 15, 100),
        p3_case(rng, 30, 30, 1000),
    ])
    cases = []
    for i in range(10):
        N = [10, 1000, 10000, 50000, 100000, 100000, 100000, 1, 100000, 100000][i]
        Q = [100, 5000, 20000, 50000, 50000, 50000, 50000, 100, 50000, 50000][i]
        cases.append(p3_case(rng, N, Q, [10, 1000, 10 ** 9][i % 3]))
    write("p3-segment", "test.txt", cases)


# ---------------------------------------------------------------- p4 조직도 관리
def p4_case(rng, Q, max_depth, chain_bias):
    used = set()

    def new_id():
        while True:
            x = rng.randint(1, 10 ** 9)
            if x not in used:
                used.add(x)
                return x

    root = new_id()
    root_num = rng.randint(1, 100)
    par = {root: 0}
    depth = {root: 0}
    total = {root: root_num}
    children = {root: []}
    alive, pos = [root], {root: 0}  # 살아있는 부서 목록 (O(1) 삭제용 인덱스)
    dead = []

    def kill(x):
        stack = [x]
        while stack:
            y = stack.pop()
            if y not in pos:
                continue
            i = pos.pop(y)
            last = alive.pop()
            if last != y:
                alive[i] = last
                pos[last] = i
            dead.append(y)
            stack.extend(children[y])

    out = [f"{Q} {root} {root_num}"]
    last_added = root
    for _ in range(Q):
        r = rng.random()
        if r < 0.55:
            if dead and rng.random() < 0.05:
                p = rng.choice(dead)
            elif rng.random() < chain_bias and last_added in pos:
                p = last_added
            else:
                p = alive[rng.randrange(len(alive))]
            if p in pos and depth[p] >= max_depth:
                p = root
            mid, num = new_id(), rng.randint(1, 100)
            if p not in pos:
                out.append(f"1 {mid} {num} {p} -1")
                continue
            par[mid], depth[mid], total[mid], children[mid] = p, depth[p] + 1, num, []
            children[p].append(mid)
            pos[mid] = len(alive)
            alive.append(mid)
            cur = p
            while cur:
                total[cur] += num
                cur = par[cur]
            last_added = mid
            out.append(f"1 {mid} {num} {p} {total[p]}")
        elif r < 0.65:
            if len(alive) > 1 and rng.random() < 0.85:
                x = root
                while x == root:
                    x = alive[rng.randrange(len(alive))]
                amount = total[x]
                cur = par[x]
                while cur:
                    total[cur] -= amount
                    cur = par[cur]
                kill(x)
                out.append(f"2 {x} {amount}")
            else:
                x = rng.choice(dead) if dead and rng.random() < 0.7 else new_id()
                out.append(f"2 {x} -1")
        else:
            if rng.random() < 0.85:
                x = alive[rng.randrange(len(alive))]
                out.append(f"3 {x} {total[x]}")
            else:
                x = rng.choice(dead) if dead and rng.random() < 0.7 else new_id()
                out.append(f"3 {x} -1")
    return out


def gen_p4(rng):
    write("p4-org", "sample.txt", [
        p4_case(rng, 10, 5, 0.3),
        p4_case(rng, 20, 5, 0.3),
        p4_case(rng, 40, 10, 0.5),
    ])
    cases = []
    for i in range(10):
        Q = [500, 2000, 5000, 10000, 20000, 30000, 30000, 30000, 30000, 30000][i]
        cases.append(p4_case(rng, Q, 100, [0.0, 0.5, 0.9][i % 3]))
    write("p4-org", "test.txt", cases)


# ---------------------------------------------------------------- p5 친구 네트워크
def p5_case(rng, N, Q):
    label = list(range(N + 1))
    members = {i: [i] for i in range(1, N + 1)}
    groups = N
    out = [f"{Q} {N}"]
    for _ in range(Q):
        r = rng.random()
        a, b = rng.randint(1, N), rng.randint(1, N)
        if r < 0.45:
            la, lb = label[a], label[b]
            if la != lb:
                if len(members[la]) < len(members[lb]):
                    la, lb = lb, la
                for x in members[lb]:
                    label[x] = la
                members[la].extend(members.pop(lb))
                groups -= 1
            out.append(f"1 {a} {b} {len(members[label[a]])}")
        elif r < 0.7:
            out.append(f"2 {a} {b} {1 if label[a] == label[b] else 0}")
        elif r < 0.9:
            out.append(f"3 {a} {len(members[label[a]])}")
        else:
            out.append(f"4 {groups}")
    return out


def gen_p5(rng):
    write("p5-union", "sample.txt", [
        p5_case(rng, 5, 10),
        p5_case(rng, 10, 20),
        p5_case(rng, 30, 40),
    ])
    cases = []
    for i in range(10):
        N = [10, 100, 1000, 10000, 100000, 100000, 100000, 1, 50000, 100000][i]
        Q = [100, 1000, 5000, 20000, 100000, 100000, 100000, 50, 100000, 100000][i]
        cases.append(p5_case(rng, N, Q))
    write("p5-union", "test.txt", cases)


# ---------------------------------------------------------------- p6 도로 네트워크
def dijkstra(adj, s, e):
    INF = float("inf")
    dist = [INF] * len(adj)
    dist[s] = 0
    heap = [(0, s)]
    while heap:
        d, u = heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist[v]:
                dist[v] = d + w
                heappush(heap, (d + w, v))
    return -1 if dist[e] == INF else dist[e]


def p6_case(rng, N, K, Q):
    adj = [[] for _ in range(N)]

    def road():
        s = rng.randrange(N)
        e = rng.randrange(N)
        while e == s:
            e = rng.randrange(N)
        return s, e, rng.randint(1, 1000)

    out = []
    roads = []
    for _ in range(K):
        s, e, t = road()
        adj[s].append((e, t))
        adj[e].append((s, t))
        roads.append(f"{s} {e} {t}")
    out.append(f"{N} {K} {Q}")
    out += roads
    for _ in range(Q):
        if rng.random() < 0.4:
            s, e, t = road()
            adj[s].append((e, t))
            adj[e].append((s, t))
            out.append(f"1 {s} {e} {t}")
        else:
            s = rng.randrange(N)
            e = s if rng.random() < 0.03 else rng.randrange(N)
            out.append(f"2 {s} {e} {dijkstra(adj, s, e)}")
    return out


def gen_p6(rng):
    write("p6-dijkstra", "sample.txt", [
        p6_case(rng, 5, 5, 10),
        p6_case(rng, 8, 10, 20),
        p6_case(rng, 15, 12, 30),
    ])
    cases = []
    for i in range(10):
        N = [10, 50, 100, 200, 500, 500, 500, 500, 300, 500][i]
        K = [8, 40, 100, 300, 2000, 1000, 400, 2000, 100, 700][i]
        Q = [100, 300, 500, 800, 1000, 1000, 1000, 1000, 1000, 1000][i]
        cases.append(p6_case(rng, N, K, Q))
    write("p6-dijkstra", "test.txt", cases)


# ---------------------------------------------------------------- p7 입국 심사
def p7_min_time(desks, M):
    lo, hi = 1, min(desks) * M
    while lo < hi:
        mid = (lo + hi) // 2
        if sum(mid // t for t in desks) >= M:
            hi = mid
        else:
            lo = mid + 1
    return lo


def p7_case(rng, N, Q, tmax, mmax):
    desks = [rng.randint(1, tmax) for _ in range(N)]
    out = [f"{N} {Q}", " ".join(map(str, desks))]
    for _ in range(Q):
        if rng.random() < 0.3 and len(desks) < 1000:
            t = rng.randint(1, tmax)
            desks.append(t)
            out.append(f"1 {t}")
        else:
            M = rng.randint(1, mmax)
            out.append(f"2 {M} {p7_min_time(desks, M)}")
    return out


def gen_p7(rng):
    write("p7-binary", "sample.txt", [
        p7_case(rng, 2, 6, 10, 10),
        p7_case(rng, 3, 10, 20, 50),
        p7_case(rng, 5, 15, 100, 100),
    ])
    cases = []
    for i in range(10):
        N = [3, 10, 50, 100, 300, 500, 800, 1, 1000, 900][i]
        Q = [30, 100, 200, 300, 300, 300, 300, 100, 300, 300][i]
        tmax = [10, 100, 10 ** 4, 10 ** 6, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9][i]
        mmax = [20, 1000, 10 ** 5, 10 ** 7, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9, 10 ** 9][i]
        cases.append(p7_case(rng, N, Q, tmax, mmax))
    write("p7-binary", "test.txt", cases)


# ---------------------------------------------------------------- p8 섬 지도 / p9 미로
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def snake(N):
    """한 줄로 길게 이어진 섬. 재귀 DFS의 깊이가 1000을 넘는다."""
    g = [[0] * N for _ in range(N)]
    for r in range(0, N, 2):
        for c in range(N):
            g[r][c] = 1
        if r + 1 < N:
            g[r + 1][N - 1 if (r // 2) % 2 == 0 else 0] = 1
    return g


def island_area(g, N, r, c):
    if g[r][c] == 0:
        return 0
    seen = {(r, c)}
    stack = [(r, c)]
    while stack:
        y, x = stack.pop()
        for dy, dx in DIRS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < N and 0 <= nx < N and g[ny][nx] and (ny, nx) not in seen:
                seen.add((ny, nx))
                stack.append((ny, nx))
    return len(seen)


def island_count(g, N):
    seen = [[False] * N for _ in range(N)]
    count = 0
    for r in range(N):
        for c in range(N):
            if g[r][c] and not seen[r][c]:
                count += 1
                seen[r][c] = True
                stack = [(r, c)]
                while stack:
                    y, x = stack.pop()
                    for dy, dx in DIRS:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < N and 0 <= nx < N and g[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
    return count


def p8_case(rng, N, Q, density, grid=None):
    g = grid or [[1 if rng.random() < density else 0 for _ in range(N)] for _ in range(N)]
    out = [f"{N} {Q}"] + [" ".join(map(str, row)) for row in g]
    for _ in range(Q):
        r = rng.random()
        y, x = rng.randrange(N), rng.randrange(N)
        if r < 0.3:
            g[y][x] = 1
            out.append(f"1 {y} {x}")
        elif r < 0.8:
            out.append(f"2 {y} {x} {island_area(g, N, y, x)}")
        else:
            out.append(f"3 {island_count(g, N)}")
    return out


def gen_p8(rng):
    write("p8-dfs", "sample.txt", [
        p8_case(rng, 4, 10, 0.4),
        p8_case(rng, 6, 15, 0.45),
        p8_case(rng, 8, 20, 0.5),
    ])
    cases = []
    for i in range(10):
        N = [5, 10, 20, 30, 50, 50, 50, 1, 50, 50][i]
        Q = [30, 100, 200, 300, 500, 500, 500, 20, 500, 500][i]
        density = [0.4, 0.3, 0.5, 0.45, 0.35, 0.5, 0.55, 0.5, 0.3, 0.4][i]
        grid = snake(N) if i in (5, 8) else None
        cases.append(p8_case(rng, N, Q, density, grid))
    write("p8-dfs", "test.txt", cases)


def bfs(g, N, sr, sc, er, ec):
    if g[sr][sc] or g[er][ec]:
        return -1
    dist = {(sr, sc): 0}
    queue = [(sr, sc)]
    for y, x in queue:
        if (y, x) == (er, ec):
            return dist[(y, x)]
        for dy, dx in DIRS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < N and 0 <= nx < N and not g[ny][nx] and (ny, nx) not in dist:
                dist[(ny, nx)] = dist[(y, x)] + 1
                queue.append((ny, nx))
    return -1


def p9_case(rng, N, Q, wall):
    g = [[1 if rng.random() < wall else 0 for _ in range(N)] for _ in range(N)]
    out = [f"{N} {Q}"] + [" ".join(map(str, row)) for row in g]
    for _ in range(Q):
        if rng.random() < 0.25:
            y, x = rng.randrange(N), rng.randrange(N)
            g[y][x] ^= 1
            out.append(f"1 {y} {x}")
        else:
            pts = []
            for _ in range(2):
                y, x = rng.randrange(N), rng.randrange(N)
                for _ in range(20):  # 대부분은 길인 칸을 고른다
                    if not g[y][x]:
                        break
                    y, x = rng.randrange(N), rng.randrange(N)
                pts.append((y, x))
            if rng.random() < 0.03:
                pts[1] = pts[0]
            (sr, sc), (er, ec) = pts
            out.append(f"2 {sr} {sc} {er} {ec} {bfs(g, N, sr, sc, er, ec)}")
    return out


def gen_p9(rng):
    write("p9-bfs", "sample.txt", [
        p9_case(rng, 4, 10, 0.25),
        p9_case(rng, 6, 15, 0.3),
        p9_case(rng, 8, 20, 0.3),
    ])
    cases = []
    for i in range(10):
        N = [5, 10, 20, 30, 40, 40, 40, 2, 40, 40][i]
        Q = [30, 100, 300, 500, 1000, 1000, 1000, 20, 1000, 1000][i]
        wall = [0.2, 0.3, 0.3, 0.25, 0.2, 0.3, 0.35, 0.3, 0.1, 0.0][i]
        cases.append(p9_case(rng, N, Q, wall))
    write("p9-bfs", "test.txt", cases)


# ---------------------------------------------------------------- p10 물류 로봇
RDR = (-1, 0, 1, 0)
RDC = (0, 1, 0, -1)


def p10_case(rng, N, Q, wall_p, id_max):
    wall = [[1 if rng.random() < wall_p else 0 for _ in range(N)] for _ in range(N)]
    robots = {}
    cell = {}
    out = [f"{N} {Q}"] + [" ".join(map(str, row)) for row in wall]
    for _ in range(Q):
        r = rng.random()
        if not robots or r < 0.2:
            mid = rng.randint(1, id_max)
            y, x, d = rng.randrange(N), rng.randrange(N), rng.randrange(4)
            if mid in robots or wall[y][x] or (y, x) in cell:
                ans = 0
            else:
                robots[mid] = [y, x, d]
                cell[(y, x)] = mid
                ans = 1
            out.append(f"1 {mid} {y} {x} {d} {ans}")
        elif r < 0.25:
            mid = rng.choice(list(robots)) if rng.random() < 0.8 else rng.randint(1, id_max)
            if mid in robots:
                y, x, _ = robots.pop(mid)
                del cell[(y, x)]
                ans = 1
            else:
                ans = 0
            out.append(f"2 {mid} {ans}")
        elif r < 0.45:
            mid = rng.choice(list(robots))
            k = rng.randint(-100, 100)
            robots[mid][2] = (robots[mid][2] + k) % 4
            out.append(f"3 {mid} {k} {robots[mid][2]}")
        elif r < 0.9:
            mid = rng.choice(list(robots))
            steps = rng.randint(1, 100) if rng.random() < 0.3 else rng.randint(1, 6)
            y, x, d = robots[mid]
            moved = 0
            for _ in range(steps):
                ny, nx = y + RDR[d], x + RDC[d]
                if not (0 <= ny < N and 0 <= nx < N) or wall[ny][nx] or (ny, nx) in cell:
                    break
                del cell[(y, x)]
                cell[(ny, nx)] = mid
                y, x = ny, nx
                moved += 1
            robots[mid][0], robots[mid][1] = y, x
            out.append(f"4 {mid} {steps} {moved}")
        else:
            if cell and rng.random() < 0.5:
                y, x = rng.choice(list(cell))
            else:
                y, x = rng.randrange(N), rng.randrange(N)
            out.append(f"5 {y} {x} {cell.get((y, x), 0)}")
    return out


def gen_p10(rng):
    write("p10-robot", "sample.txt", [
        p10_case(rng, 4, 12, 0.1, 4),
        p10_case(rng, 5, 20, 0.15, 5),
        p10_case(rng, 6, 30, 0.1, 6),
    ])
    cases = []
    for i in range(10):
        N = [5, 8, 12, 20, 30, 50, 50, 2, 50, 40][i]
        Q = [100, 500, 2000, 5000, 10000, 30000, 30000, 100, 30000, 30000][i]
        wall = [0.1, 0.1, 0.15, 0.1, 0.05, 0.1, 0.02, 0.0, 0.2, 0.1][i]
        id_max = [5, 10, 20, 50, 100, 300, 1000, 3, 30, 1000][i]
        cases.append(p10_case(rng, N, Q, wall, id_max))
    write("p10-robot", "test.txt", cases)


# ---------------------------------------------------------------- p11 사무실 프린터
def p11_case(rng, N, Q, pmax, dtmax):
    """1초씩 시간을 흘려보내는 방식으로 정답을 만든다 (모범 답안의 이벤트 방식과 다른 방법)."""
    end = [None] * N
    queue = []
    qhead = 0
    finished = 0
    running = 0
    processed = -1
    now = 0
    job = 0
    out = [f"{N} {Q}"]

    def tick_to(t):
        nonlocal finished, running, processed, qhead
        if running == 0 and qhead == len(queue):
            processed = t
            return
        for x in range(processed + 1, t + 1):
            for p in range(N):
                if end[p] == x:
                    end[p] = None
                    finished += 1
                    running -= 1
            for p in range(N):
                if end[p] is None and qhead < len(queue):
                    end[p] = x + queue[qhead]
                    qhead += 1
                    running += 1
            if running == 0 and qhead == len(queue):
                break
        processed = t

    for _ in range(Q):
        now += rng.randint(0, dtmax)
        tick_to(now)
        r = rng.random()
        if r < 0.6:
            job += 1
            pages = rng.randint(1, pmax)
            idle = next((p for p in range(N) if end[p] is None), -1)
            if idle >= 0:
                end[idle] = now + pages
                running += 1
            else:
                queue.append(pages)
            out.append(f"1 {now} {job} {pages} {idle}")
        elif r < 0.8:
            out.append(f"2 {now} {finished}")
        else:
            out.append(f"3 {now} {len(queue) - qhead}")
    return out


def gen_p11(rng):
    write("p11-printer", "sample.txt", [
        p11_case(rng, 2, 12, 6, 2),
        p11_case(rng, 3, 20, 8, 2),
        p11_case(rng, 1, 25, 5, 1),
    ])
    cases = []
    for i in range(10):
        N = [1, 2, 3, 5, 8, 10, 20, 50, 3, 4][i]
        Q = [100, 500, 2000, 5000, 10000, 30000, 30000, 30000, 30000, 30000][i]
        pmax = [5, 8, 10, 20, 20, 20, 20, 20, 3, 20][i]
        dtmax = [2, 2, 2, 2, 2, 2, 1, 1, 30, 30][i]
        cases.append(p11_case(rng, N, Q, pmax, dtmax))
    write("p11-printer", "test.txt", cases)


GENERATORS = {"p10-robot": gen_p10, "p11-printer": gen_p11, "p1-word": gen_p1, "p2-ranking": gen_p2, "p3-segment": gen_p3, "p4-org": gen_p4,
              "p5-union": gen_p5, "p6-dijkstra": gen_p6, "p7-binary": gen_p7, "p8-dfs": gen_p8, "p9-bfs": gen_p9}

if __name__ == "__main__":
    targets = sys.argv[1:] or list(GENERATORS)
    for pid in targets:
        GENERATORS[pid](random.Random(f"swb-{pid}"))
        print("generated", pid)
