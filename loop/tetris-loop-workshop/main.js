(function () {
  const {
    BOARD_WIDTH,
    BOARD_HEIGHT,
    GAME_STATUS,
    pickTetrominoType,
    getLevel,
    getDropInterval,
    togglePause,
    randomForType,
    calculateGhostY,
    holdPiece,
    createInitialState,
    startGame,
    restartGame,
    getPieceCells,
    moveLeft,
    moveRight,
    moveDown,
    rotateClockwise,
    lockAndScore,
    softDrop,
    hardDrop,
    LEADERBOARD_KEY,
    validateName,
    addLeaderboardEntry,
    parseLeaderboard,
    serializeLeaderboard,
  } = globalThis.TetrisGame;
  let state = createInitialState();
  let dropTimer = null;
  let dropTimerInterval = null;
  // 다음 블록 종류. 블록을 새로 놓을 때 randomForType으로 주입하고 바로 새로 뽑는다(게임 상태는 그대로).
  let nextType = null;

  const boardEl = document.getElementById('board');
  const cells = [];
  for (let row = 0; row < BOARD_HEIGHT; row++) {
    const rowCells = [];
    for (let col = 0; col < BOARD_WIDTH; col++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.row = String(row);
      cell.dataset.col = String(col);
      boardEl.appendChild(cell);
      rowCells.push(cell);
    }
    cells.push(rowCells);
  }

  // 연출 전용 레이어. 게임 상태는 읽기만 하고, 효과 요소는 끝나면 스스로 지워진다.
  const fxLayer = document.createElement('div');
  fxLayer.className = 'fx-layer';
  boardEl.appendChild(fxLayer);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const FX_MAX_MS = 2000;

  function cellBox(row, col) {
    const cell = cells[row][col];
    return { left: cell.offsetLeft, top: cell.offsetTop, width: cell.offsetWidth, height: cell.offsetHeight };
  }

  function addFx(className, styles, parent = fxLayer) {
    const el = document.createElement('div');
    el.className = className;
    Object.entries(styles).forEach(([key, value]) => {
      if (key.startsWith('--')) el.style.setProperty(key, value);
      else el.style[key] = value;
    });
    el.addEventListener('animationend', (event) => {
      if (event.target === el) el.remove();
    });
    setTimeout(() => el.remove(), FX_MAX_MS);
    parent.appendChild(el);
    return el;
  }

  const px = (n) => n + 'px';
  const randomBetween = (min, max) => min + Math.random() * (max - min);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];
  const gem = (type) => 'var(--gem-' + type + ')';

  function playLockFx(lockedCells) {
    lockedCells.forEach(([row, col]) => {
      const box = cellBox(row, col);
      addFx('fx-lock', { left: px(box.left), top: px(box.top), width: px(box.width), height: px(box.height) });
    });
  }

  function playBurst(x, y, colors, delayMs) {
    const burst = addFx('fx-burst', { left: px(x), top: px(y), '--delay': delayMs + 'ms' });
    addFx('fx-ring', {}, burst);
    const rays = 16;
    const radius = randomBetween(48, 70);
    for (let i = 0; i < rays; i++) {
      addFx('fx-ray', { '--a': (360 / rays) * i + 'deg', '--r': px(radius), '--c': pick(colors) }, burst);
    }
  }

  // clearedRows: [{ row, types }] — 지워지기 직전 줄 번호와 그 줄에 있던 블록 종류
  function playClearFx(clearedRows) {
    const left = cellBox(0, 0).left;
    const width = cellBox(0, BOARD_WIDTH - 1).left + cellBox(0, BOARD_WIDTH - 1).width - left;
    const palette = ['var(--gold)', 'var(--gold-light)'];
    clearedRows.forEach(({ row, types }) => {
      const box = cellBox(row, 0);
      addFx('fx-band', { left: px(left), top: px(box.top), width: px(width), height: px(box.height) });
      if (reduceMotion.matches) return;
      const colors = palette.concat(types.map(gem));
      for (let i = 0; i < 14; i++) {
        addFx('fx-spark', {
          left: px(left + randomBetween(0.05, 0.95) * width),
          top: px(box.top + box.height / 2),
          '--s': px(randomBetween(7, 12)),
          '--c': pick(colors),
          '--dx': px(randomBetween(-60, 60)),
          '--dy': px(randomBetween(-70, -15)),
          '--rot': randomBetween(-180, 180) + 'deg',
          '--d': Math.round(randomBetween(750, 1000)) + 'ms',
        });
      }
    });
    if (reduceMotion.matches || clearedRows.length < 2) return;
    const height = boardEl.clientHeight;
    const colors = palette.concat(clearedRows.flatMap(({ types }) => types.map(gem)));
    for (let i = 0; i < clearedRows.length - 1; i++) {
      playBurst(randomBetween(0.25, 0.75) * width + left, randomBetween(0.25, 0.7) * height, colors, i * 160);
    }
    if (clearedRows.length >= 4) {
      boardEl.classList.remove('fx-shake');
      void boardEl.offsetWidth; // 같은 애니메이션을 다시 시작하게 한다
      boardEl.classList.add('fx-shake');
    }
  }

  boardEl.addEventListener('animationend', (event) => {
    if (event.target === boardEl) boardEl.classList.remove('fx-shake');
  });

  // 고정 직전 상태로, 고정되면 가득 찰 줄과 그 줄의 블록 종류를 구한다.
  function rowsFilledByLock(board, piece) {
    const lockedCells = getPieceCells(piece);
    const locked = new Set(lockedCells.map(([r, c]) => r + ',' + c));
    const rows = [...new Set(lockedCells.map(([r]) => r))].sort((a, b) => a - b);
    return rows
      .filter((r) => board[r].every((v, c) => v !== 0 || locked.has(r + ',' + c)))
      .map((r) => ({
        row: r,
        types: [...new Set(board[r].filter((v) => v !== 0).concat(piece.type))],
      }));
  }

  const scoreEl = document.getElementById('score');
  const linesEl = document.getElementById('lines');
  const statusEl = document.getElementById('status');
  const startButton = document.getElementById('start');
  const levelEl = document.getElementById('level');
  // 일시정지 안내는 보드 위에 겹쳐 보이도록 보드 안으로 옮긴다.
  const pauseNote = document.getElementById('pause-note');
  boardEl.appendChild(pauseNote);

  const PREVIEW_SIZE = 4;
  function createMiniGrid(container) {
    return Array.from({ length: PREVIEW_SIZE * PREVIEW_SIZE }, () => {
      const cell = document.createElement('div');
      cell.className = 'cell';
      container.appendChild(cell);
      return cell;
    });
  }
  const previewCells = createMiniGrid(document.getElementById('next-preview'));
  const holdEl = document.getElementById('hold-preview');
  const holdCells = createMiniGrid(holdEl);

  function render() {
    for (let row = 0; row < BOARD_HEIGHT; row++) {
      for (let col = 0; col < BOARD_WIDTH; col++) {
        const fixed = state.board[row][col];
        cells[row][col].className = fixed ? 'cell piece-' + fixed : 'cell';
      }
    }
    if (state.activePiece) {
      // 고스트를 먼저 그리고 그 위에 현재 블록을 그린다(겹치는 칸은 현재 블록이 보인다).
      const ghost = { ...state.activePiece, row: calculateGhostY(state.board, state.activePiece) };
      getPieceCells(ghost).forEach(([row, col]) => {
        cells[row][col].className = 'cell ghost-' + ghost.type;
      });
    }
    if (state.activePiece) {
      getPieceCells(state.activePiece).forEach(([row, col]) => {
        cells[row][col].className = 'cell piece-' + state.activePiece.type;
      });
    }
    scoreEl.textContent = String(state.score);
    linesEl.textContent = String(state.lines);
    levelEl.textContent = String(getLevel(state.lines));
    statusEl.textContent = state.status;
    startButton.textContent = state.status === GAME_STATUS.GAME_OVER ? '재시작' : '시작';
    startButton.disabled =
      state.status === GAME_STATUS.PLAYING ||
      state.status === GAME_STATUS.LANDED ||
      state.status === GAME_STATUS.PAUSED;
    pauseNote.hidden = state.status !== GAME_STATUS.PAUSED;
    renderPreview();
  }

  // 4×4 칸 가운데에 type 블록을 생성 방향으로 그린다. type이 없으면 비운다.
  function drawMini(miniCells, type) {
    miniCells.forEach((cell) => {
      cell.className = 'cell';
    });
    if (!type) return;
    const shape = getPieceCells({ type, row: 0, col: 0, rotation: 0 });
    const rows = shape.map(([r]) => r);
    const cols = shape.map(([, c]) => c);
    const top = Math.min(...rows);
    const left = Math.min(...cols);
    const rowOffset = Math.floor((PREVIEW_SIZE - (Math.max(...rows) - top + 1)) / 2);
    const colOffset = Math.floor((PREVIEW_SIZE - (Math.max(...cols) - left + 1)) / 2);
    shape.forEach(([r, c]) => {
      miniCells[(r - top + rowOffset) * PREVIEW_SIZE + (c - left + colOffset)].className = 'cell piece-' + type;
    });
  }

  // 다음 블록은 READY·GAME_OVER에서 비운다. 홀드 칸은 보관한 블록을 보여주고, 이번 블록에서 이미 썼으면 흐리게.
  function renderPreview() {
    const showing = state.status !== GAME_STATUS.READY && state.status !== GAME_STATUS.GAME_OVER;
    drawMini(previewCells, showing ? nextType : null);
    drawMini(holdCells, state.holdType);
    holdEl.classList.toggle('is-used', Boolean(state.holdUsed));
  }

  // 지금 놓을 블록 종류를 주입할 random을 돌려주고, 다음 블록을 새로 뽑는다.
  function takeNext() {
    if (!nextType) nextType = pickTetrominoType();
    const random = randomForType(nextType);
    nextType = pickTetrominoType();
    return random;
  }

  function currentDropInterval() {
    return getDropInterval(getLevel(state.lines));
  }

  function stopDropTimer() {
    clearInterval(dropTimer);
    dropTimer = null;
    dropTimerInterval = null;
  }

  // 낙하 타이머를 처음부터 다시 센다. 항상 타이머 하나만 돌고, 간격은 현재 레벨을 따른다.
  function restartDropTimer() {
    stopDropTimer();
    dropTimerInterval = currentDropInterval();
    dropTimer = setInterval(drop, dropTimerInterval);
  }

  // ---------- 리더보드 ----------
  const saveForm = document.getElementById('save-form');
  const nameInput = document.getElementById('player-name');
  const saveMessage = document.getElementById('save-message');
  const leaderboardEl = document.getElementById('leaderboard');
  const leaderboardMessage = document.getElementById('leaderboard-message');
  const MSG_NAME = '이름은 앞뒤 공백을 빼고 2~10자로 입력하세요.';
  const MSG_NOT_RANKED = 'TOP 10에 들지 못해 저장되지 않았습니다.';
  const MSG_NO_STORAGE = '이 브라우저에서는 기록을 저장할 수 없습니다.';
  const MSG_EMPTY = '아직 기록이 없습니다.';

  let storageOk = true;
  let savedThisGame = false;
  let highlightId = null;
  let leaderboard = loadLeaderboard();

  // 저장소 접근은 예외가 나도 게임이 멈추지 않도록 모두 try/catch로 감싼다.
  function loadLeaderboard() {
    try {
      return parseLeaderboard(window.localStorage.getItem(LEADERBOARD_KEY));
    } catch (e) {
      storageOk = false;
      return [];
    }
  }

  function storeLeaderboard(list) {
    try {
      window.localStorage.setItem(LEADERBOARD_KEY, serializeLeaderboard(list));
      return true;
    } catch (e) {
      storageOk = false;
      return false;
    }
  }

  function textSpan(className, text) {
    const span = document.createElement('span');
    span.className = className;
    span.textContent = text;
    return span;
  }

  function renderLeaderboard() {
    leaderboardEl.replaceChildren(
      ...leaderboard.map((entry, i) => {
        const li = document.createElement('li');
        if (entry.id === highlightId) li.className = 'is-new';
        li.append(
          textSpan('rank', String(i + 1)),
          textSpan('name', entry.name),
          textSpan('points', String(entry.score)),
          textSpan('cleared', entry.clearedLines + '줄')
        );
        return li;
      })
    );
    if (!storageOk) leaderboardMessage.textContent = MSG_NO_STORAGE;
    else leaderboardMessage.textContent = leaderboard.length ? '' : MSG_EMPTY;
  }

  function openSaveForm() {
    savedThisGame = false;
    nameInput.value = '';
    saveMessage.textContent = '';
    saveForm.hidden = false;
    nameInput.focus();
  }

  function closeSaveForm() {
    saveForm.hidden = true;
    saveMessage.textContent = '';
  }

  saveForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (savedThisGame || state.status !== GAME_STATUS.GAME_OVER) return;
    if (!storageOk) {
      saveMessage.textContent = MSG_NO_STORAGE;
      return;
    }
    const { ok, name } = validateName(nameInput.value);
    if (!ok) {
      saveMessage.textContent = MSG_NAME;
      return;
    }
    const playedAt = new Date().toISOString();
    const entry = {
      id: playedAt + '-' + Math.random().toString(36).slice(2, 8),
      name,
      score: state.score,
      clearedLines: state.lines,
      playedAt,
    };
    const next = addLeaderboardEntry(leaderboard, entry);
    if (!next.includes(entry)) {
      savedThisGame = true;
      saveForm.hidden = true;
      saveMessage.textContent = MSG_NOT_RANKED;
      return;
    }
    if (!storeLeaderboard(next)) {
      saveMessage.textContent = MSG_NO_STORAGE;
      renderLeaderboard();
      return;
    }
    savedThisGame = true;
    leaderboard = next;
    highlightId = entry.id;
    closeSaveForm();
    renderLeaderboard();
  });

  // ---------- 게임 진행 ----------
  function update(next) {
    const wasOver = state.status === GAME_STATUS.GAME_OVER;
    state = next;
    if (state.status === GAME_STATUS.GAME_OVER) {
      stopDropTimer();
      if (!wasOver) openSaveForm();
    } else if (dropTimer && dropTimerInterval !== currentDropInterval()) {
      // 레벨이 올라 간격이 바뀌면 다음 낙하부터 새 간격을 쓴다.
      restartDropTimer();
    }
    render();
  }

  // landed: 고정 직전(LANDED) 상태, next: 고정 결과. 연출은 고정 직전 상태로 계산한다.
  function settle(landed, next) {
    const lockedCells = getPieceCells(landed.activePiece);
    const clearedRows = rowsFilledByLock(landed.board, landed.activePiece);
    update(next);
    playLockFx(lockedCells);
    if (clearedRows.length) playClearFx(clearedRows);
  }

  // PLAYING이면 한 칸 낙하, LANDED이면 고정하고 다음 블록을 놓는다.
  function drop() {
    if (state.status === GAME_STATUS.PLAYING) update(moveDown(state));
    else if (state.status === GAME_STATUS.LANDED) settle(state, lockAndScore(state, takeNext()));
  }

  function hardDropWithFx() {
    let landed = state;
    while (landed.status === GAME_STATUS.PLAYING) landed = moveDown(landed);
    settle(landed, hardDrop(state, takeNext()));
  }

  startButton.addEventListener('click', () => {
    if (state.status === GAME_STATUS.READY) {
      nextType = null;
      update(startGame(state, takeNext()));
    } else if (state.status === GAME_STATUS.GAME_OVER) {
      nextType = null;
      update(restartGame(state, takeNext()));
      closeSaveForm();
    }
    if (state.status === GAME_STATUS.PLAYING) restartDropTimer();
  });

  const KEY_ACTIONS = {
    ArrowLeft: moveLeft,
    ArrowRight: moveRight,
    ArrowDown: softDrop,
    ArrowUp: rotateClockwise,
  };

  document.addEventListener('keydown', (event) => {
    // 이름 입력칸에서는 어떤 키도 게임이 가로채지 않는다.
    if (event.target === nameInput) return;
    // 일시정지: 키 위치(KeyP) 기준이라 대소문자·한글 자판(ㅔ) 모두 같다.
    // 홀드: 키 위치(KeyC) 기준. 홀드 칸이 비었을 때만 다음 블록(미리보기)을 쓴다.
    if (event.code === 'KeyC') {
      if (state.status !== GAME_STATUS.PLAYING || state.holdUsed) return;
      update(holdPiece(state, state.holdType == null ? takeNext() : undefined));
      if (state.status === GAME_STATUS.PLAYING) restartDropTimer();
      return;
    }
    if (event.code === 'KeyP') {
      if (state.status !== GAME_STATUS.PLAYING && state.status !== GAME_STATUS.PAUSED) return;
      update(togglePause(state));
      if (state.status === GAME_STATUS.PAUSED) stopDropTimer();
      else restartDropTimer();
      return;
    }
    if (event.key === ' ') {
      event.preventDefault();
      if (state.status !== GAME_STATUS.PLAYING) return;
      hardDropWithFx();
      if (state.status === GAME_STATUS.PLAYING) restartDropTimer();
      return;
    }
    const action = KEY_ACTIONS[event.key];
    if (!action) return;
    event.preventDefault();
    if (state.status !== GAME_STATUS.PLAYING) return;
    update(action(state));
    // ↓는 LANDED가 된 경우에도 타이머를 초기화해 고정이 누른 시점부터 현재 낙하 간격 뒤가 되게 한다.
    if (event.key === 'ArrowDown') restartDropTimer();
  });

  render();
  renderLeaderboard();
})();
