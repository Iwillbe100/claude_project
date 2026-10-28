# 모범 답안: 단어 개수와 "모든 접두사의 개수"를 각각 딕셔너리로 관리한다.
# 단어 길이가 10 이하이므로 add/remove 시 접두사 10개를 갱신해도 충분히 빠르다.

word_cnt = {}
prefix_cnt = {}


def init() -> None:
    global word_cnt, prefix_cnt
    word_cnt = {}
    prefix_cnt = {}


def add(mWord: str) -> int:
    word_cnt[mWord] = word_cnt.get(mWord, 0) + 1
    for i in range(1, len(mWord) + 1):
        p = mWord[:i]
        prefix_cnt[p] = prefix_cnt.get(p, 0) + 1
    return word_cnt[mWord]


def removeWord(mWord: str) -> int:
    c = word_cnt.get(mWord, 0)
    if c == 0:
        return -1
    word_cnt[mWord] = c - 1
    for i in range(1, len(mWord) + 1):
        prefix_cnt[mWord[:i]] -= 1
    return c - 1


def countPrefix(mPrefix: str) -> int:
    return prefix_cnt.get(mPrefix, 0)
