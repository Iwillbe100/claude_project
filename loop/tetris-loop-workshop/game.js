(function () {
  const BOARD_WIDTH = 10;
  const BOARD_HEIGHT = 20;
  const DROP_INTERVAL_MS = 700;

  const LINE_SCORES = Object.freeze([0, 100, 300, 500, 800]);
  const SOFT_DROP_SCORE = 1;
  const HARD_DROP_SCORE = 2;
  const LEADERBOARD_KEY = 'tetris-loop.leaderboard.v1';
  const LEADERBOARD_SIZE = 10;

  const LEVEL_LINES = 10;
  const MIN_DROP_INTERVAL_MS = 100;
  const DROP_INTERVAL_STEP_MS = 60;

  const GAME_STATUS = Object.freeze({
    READY: 'READY',
    PLAYING: 'PLAYING',
    LANDED: 'LANDED',
    PAUSED: 'PAUSED',
    GAME_OVER: 'GAME_OVER',
  });

  const TETROMINO_TYPES = Object.freeze(['I', 'O', 'T', 'S', 'Z', 'J', 'L']);

  // 생성 방향(rotation 0)의 셀 좌표 [행, 열]. SRS 회전 상자 안의 상대 좌표다.
  const TETROMINOES = deepFreeze({
    I: [[1, 0], [1, 1], [1, 2], [1, 3]],
    O: [[0, 1], [0, 2], [1, 1], [1, 2]],
    T: [[0, 1], [1, 0], [1, 1], [1, 2]],
    S: [[0, 1], [0, 2], [1, 0], [1, 1]],
    Z: [[0, 0], [0, 1], [1, 1], [1, 2]],
    J: [[0, 0], [1, 0], [1, 1], [1, 2]],
    L: [[0, 2], [1, 0], [1, 1], [1, 2]],
  });

  // 회전 상자 크기. O는 회전하지 않는다(0).
  const ROTATION_BOX = { I: 4, O: 0, T: 3, S: 3, Z: 3, J: 3, L: 3 };

  // ROTATIONS[type][rotation]: 시계방향으로 rotation번 돌린 상대 좌표.
  const ROTATIONS = {};
  TETROMINO_TYPES.forEach((type) => {
    const n = ROTATION_BOX[type];
    const states = [TETROMINOES[type]];
    for (let i = 1; i < 4; i++) {
      const prev = states[i - 1];
      states.push(n ? prev.map(([r, c]) => [c, n - 1 - r]) : prev);
    }
    ROTATIONS[type] = states;
  });

  function deepFreeze(obj) {
    Object.values(obj).forEach((v) => {
      if (v && typeof v === 'object') deepFreeze(v);
    });
    return Object.freeze(obj);
  }

  function createEmptyBoard() {
    return Array.from({ length: BOARD_HEIGHT }, () => Array(BOARD_WIDTH).fill(0));
  }

  function createInitialState() {
    return {
      board: createEmptyBoard(),
      score: 0,
      lines: 0,
      status: GAME_STATUS.READY,
      activePiece: null,
      holdType: null,
      holdUsed: false,
    };
  }

  function pickTetrominoType(random = Math.random) {
    return TETROMINO_TYPES[Math.floor(random() * TETROMINO_TYPES.length)];
  }

  // 가장 위 셀이 0행, 가장 왼쪽 셀이 Math.floor((10 - 너비) / 2)열이 되도록 기준점을 정한다.
  function spawnPiece(type) {
    const cells = TETROMINOES[type];
    const rows = cells.map(([r]) => r);
    const cols = cells.map(([, c]) => c);
    const minCol = Math.min(...cols);
    const width = Math.max(...cols) - minCol + 1;
    return {
      type,
      row: -Math.min(...rows),
      col: Math.floor((BOARD_WIDTH - width) / 2) - minCol,
      rotation: 0,
    };
  }

  function getPieceCells(piece) {
    const offsets = ROTATIONS[piece.type][piece.rotation || 0];
    return offsets.map(([r, c]) => [piece.row + r, piece.col + c]);
  }

  function isInsideBoard(piece) {
    return getPieceCells(piece).every(
      ([r, c]) => r >= 0 && r < BOARD_HEIGHT && c >= 0 && c < BOARD_WIDTH
    );
  }

  // 보드 안이고 고정된 셀과 겹치지 않으면 true.
  function canPlace(board, piece) {
    return isInsideBoard(piece) && getPieceCells(piece).every(([r, c]) => board[r][c] === 0);
  }

  // 가득 찬 행을 지우고 남은 행을 아래로 모은 새 보드와 지운 행 수를 반환한다.
  function clearLines(board) {
    const kept = board.filter((row) => row.some((cell) => cell === 0)).map((row) => row.slice());
    const cleared = BOARD_HEIGHT - kept.length;
    const empty = Array.from({ length: cleared }, () => Array(BOARD_WIDTH).fill(0));
    return { board: empty.concat(kept), cleared };
  }

  function startGame(state, random) {
    if (state.status !== GAME_STATUS.READY) return state;
    return {
      ...state,
      status: GAME_STATUS.PLAYING,
      activePiece: spawnPiece(pickTetrominoType(random)),
    };
  }

  function tryPiece(state, piece) {
    return canPlace(state.board, piece) ? { ...state, activePiece: piece } : state;
  }

  function moveLeft(state) {
    if (state.status !== GAME_STATUS.PLAYING) return state;
    return tryPiece(state, { ...state.activePiece, col: state.activePiece.col - 1 });
  }

  function moveRight(state) {
    if (state.status !== GAME_STATUS.PLAYING) return state;
    return tryPiece(state, { ...state.activePiece, col: state.activePiece.col + 1 });
  }

  function moveDown(state) {
    if (state.status !== GAME_STATUS.PLAYING) return state;
    const moved = { ...state.activePiece, row: state.activePiece.row + 1 };
    if (canPlace(state.board, moved)) return { ...state, activePiece: moved };
    return { ...state, status: GAME_STATUS.LANDED };
  }

  function rotateClockwise(state) {
    if (state.status !== GAME_STATUS.PLAYING) return state;
    const piece = state.activePiece;
    return tryPiece(state, { ...piece, rotation: ((piece.rotation || 0) + 1) % 4 });
  }

  // LANDED 블록을 보드에 쓰고, 줄을 지우고, 다음 블록을 놓는다. 놓을 수 없으면 GAME_OVER.
  function lockPiece(state, random) {
    if (state.status !== GAME_STATUS.LANDED) return state;
    const piece = state.activePiece;
    const written = state.board.map((row) => row.slice());
    getPieceCells(piece).forEach(([r, c]) => {
      written[r][c] = piece.type;
    });
    const { board, cleared } = clearLines(written);
    const next = spawnPiece(pickTetrominoType(random));
    // 블록이 고정되면 다시 홀드할 수 있다.
    const base = { ...state, board, lines: state.lines + cleared, holdUsed: false };
    if (canPlace(board, next)) return { ...base, status: GAME_STATUS.PLAYING, activePiece: next };
    return { ...base, status: GAME_STATUS.GAME_OVER, activePiece: null };
  }

  // 지금 위치에서 바로 떨어뜨리면 놓일 row. 이미 내려갈 수 없으면 piece.row.
  function calculateGhostY(board, piece) {
    let row = piece.row;
    while (canPlace(board, { ...piece, row: row + 1 })) row++;
    return row;
  }

  // 빈 홀드: 현재 블록을 보관하고 random으로 고른 블록을 놓는다. 찬 홀드: 서로 바꾼다. 블록당 1회.
  function holdPiece(state, random) {
    if (state.status !== GAME_STATUS.PLAYING || state.holdUsed) return state;
    const currentType = state.activePiece.type;
    const nextType = state.holdType == null ? pickTetrominoType(random) : state.holdType;
    const next = spawnPiece(nextType);
    const base = { ...state, holdType: currentType, holdUsed: true };
    if (canPlace(state.board, next)) return { ...base, activePiece: next };
    return { ...base, status: GAME_STATUS.GAME_OVER, activePiece: null };
  }

  // lockPiece에 줄 제거 점수를 더한다. lockPiece 자체는 점수를 바꾸지 않는다.
  function lockAndScore(state, random) {
    const next = lockPiece(state, random);
    if (next === state) return state;
    return { ...next, score: next.score + LINE_SCORES[next.lines - state.lines] };
  }

  // ↓: moveDown과 같게 움직이고, 실제로 한 칸 내려갔을 때만 1점.
  function softDrop(state) {
    const next = moveDown(state);
    if (next === state || next.status !== GAME_STATUS.PLAYING) return next;
    return { ...next, score: next.score + SOFT_DROP_SCORE };
  }

  // Space: 내려갈 수 있는 만큼 내린 뒤(칸당 2점) 바로 고정한다.
  function hardDrop(state, random) {
    if (state.status !== GAME_STATUS.PLAYING) return state;
    let piece = state.activePiece;
    let distance = 0;
    while (canPlace(state.board, { ...piece, row: piece.row + 1 })) {
      piece = { ...piece, row: piece.row + 1 };
      distance++;
    }
    const landed = {
      ...state,
      activePiece: piece,
      status: GAME_STATUS.LANDED,
      score: state.score + distance * HARD_DROP_SCORE,
    };
    return lockAndScore(landed, random);
  }

  function validateName(raw) {
    const name = String(raw == null ? '' : raw).trim();
    const length = [...name].length;
    return { ok: length >= 2 && length <= 10, name };
  }

  function isLeaderboardEntry(entry) {
    return (
      entry !== null &&
      typeof entry === 'object' &&
      typeof entry.id === 'string' &&
      typeof entry.name === 'string' &&
      validateName(entry.name).ok &&
      Number.isFinite(entry.score) &&
      Number.isFinite(entry.clearedLines) &&
      typeof entry.playedAt === 'string'
    );
  }

  // 점수 내림차순, 같은 점수는 playedAt이 이른(먼저 세운) 기록 먼저.
  function compareEntries(a, b) {
    if (b.score !== a.score) return b.score - a.score;
    if (a.playedAt < b.playedAt) return -1;
    if (a.playedAt > b.playedAt) return 1;
    return 0;
  }

  function addLeaderboardEntry(list, entry) {
    return list.concat([entry]).sort(compareEntries).slice(0, LEADERBOARD_SIZE);
  }

  function parseLeaderboard(text) {
    if (typeof text !== 'string') return [];
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      return [];
    }
    if (!Array.isArray(data)) return [];
    return data
      .filter(isLeaderboardEntry)
      .map(({ id, name, score, clearedLines, playedAt }) => ({ id, name, score, clearedLines, playedAt }))
      .sort(compareEntries)
      .slice(0, LEADERBOARD_SIZE);
  }

  function serializeLeaderboard(list) {
    return JSON.stringify(list);
  }

  function getLevel(lines) {
    return Math.floor(lines / LEVEL_LINES) + 1;
  }

  function getDropInterval(level) {
    return Math.max(MIN_DROP_INTERVAL_MS, DROP_INTERVAL_MS - (level - 1) * DROP_INTERVAL_STEP_MS);
  }

  // PLAYING ↔ PAUSED만 오간다. 그 밖의 상태는 그대로.
  function togglePause(state) {
    if (state.status === GAME_STATUS.PLAYING) return { ...state, status: GAME_STATUS.PAUSED };
    if (state.status === GAME_STATUS.PAUSED) return { ...state, status: GAME_STATUS.PLAYING };
    return state;
  }

  // pickTetrominoType에 넘기면 항상 type이 나오는 random. 다음 블록 미리보기를 기존 주입 지점으로 넘길 때 쓴다.
  function randomForType(type) {
    const index = TETROMINO_TYPES.indexOf(type);
    return () => (index + 0.5) / TETROMINO_TYPES.length;
  }

  function restartGame(state, random) {
    if (state.status !== GAME_STATUS.LANDED && state.status !== GAME_STATUS.GAME_OVER) return state;
    return startGame(createInitialState(), random);
  }

  globalThis.TetrisGame = {
    BOARD_WIDTH,
    BOARD_HEIGHT,
    DROP_INTERVAL_MS,
    LINE_SCORES,
    SOFT_DROP_SCORE,
    HARD_DROP_SCORE,
    LEADERBOARD_KEY,
    LEADERBOARD_SIZE,
    LEVEL_LINES,
    MIN_DROP_INTERVAL_MS,
    DROP_INTERVAL_STEP_MS,
    GAME_STATUS,
    TETROMINO_TYPES,
    TETROMINOES,
    createEmptyBoard,
    createInitialState,
    pickTetrominoType,
    getPieceCells,
    isInsideBoard,
    canPlace,
    clearLines,
    startGame,
    moveLeft,
    moveRight,
    moveDown,
    rotateClockwise,
    lockPiece,
    lockAndScore,
    softDrop,
    hardDrop,
    restartGame,
    validateName,
    addLeaderboardEntry,
    parseLeaderboard,
    serializeLeaderboard,
    getLevel,
    getDropInterval,
    togglePause,
    randomForType,
    calculateGhostY,
    holdPiece,
  };
})();
