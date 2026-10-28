(function () {
  const results = [];

  function test(name, fn) {
    try {
      fn();
      results.push({ name, ok: true });
    } catch (e) {
      results.push({ name, ok: false, reason: e && e.message ? e.message : String(e) });
    }
  }

  function assert(cond, message) {
    if (!cond) throw new Error(message);
  }

  function assertEqual(actual, expected, label) {
    assert(actual === expected, label + ': 기대 ' + String(expected) + ', 실제 ' + String(actual));
  }

  const G = globalThis.TetrisGame;

  test('globalThis.TetrisGame이 존재한다', () => {
    assert(G && typeof G === 'object', 'TetrisGame 객체가 없다');
  });

  test('필수 함수와 상수가 존재한다', () => {
    assert(G, 'TetrisGame 객체가 없다');
    assertEqual(typeof G.createEmptyBoard, 'function', 'createEmptyBoard 타입');
    assertEqual(typeof G.createInitialState, 'function', 'createInitialState 타입');
    assert(G.GAME_STATUS && typeof G.GAME_STATUS === 'object', 'GAME_STATUS가 객체가 아니다');
  });

  test('보드 너비와 높이 상수', () => {
    assertEqual(G.BOARD_WIDTH, 10, 'BOARD_WIDTH');
    assertEqual(G.BOARD_HEIGHT, 20, 'BOARD_HEIGHT');
  });

  test('GAME_STATUS 값', () => {
    ['READY', 'PLAYING', 'LANDED', 'PAUSED', 'GAME_OVER'].forEach((key) => {
      assertEqual(G.GAME_STATUS[key], key, 'GAME_STATUS.' + key);
    });
  });

  test('빈 보드는 20행×10열이고 모든 셀이 0이다', () => {
    const board = G.createEmptyBoard();
    assertEqual(board.length, 20, '행 수');
    board.forEach((row, r) => {
      assert(Array.isArray(row), r + '행이 배열이 아니다');
      assertEqual(row.length, 10, r + '행의 셀 수');
      row.forEach((cell, c) => assertEqual(cell, 0, '셀 [' + r + '][' + c + ']'));
    });
  });

  test('두 번 만든 빈 보드는 행 배열을 공유하지 않는다', () => {
    const a = G.createEmptyBoard();
    const b = G.createEmptyBoard();
    assert(a !== b, '보드 객체를 공유한다');
    a.forEach((row, r) => assert(row !== b[r], r + '행이 두 보드에서 공유된다'));
    for (let r = 0; r < a.length; r++) {
      for (let s = r + 1; s < a.length; s++) {
        assert(a[r] !== a[s], r + '행과 ' + s + '행이 같은 배열이다');
      }
    }
    a[0][0] = 1;
    assertEqual(b[0][0], 0, '다른 보드의 셀');
    assertEqual(a[1][0], 0, '같은 보드 다른 행의 셀');
  });

  test('초기 상태의 점수, 줄 수, 게임 상태', () => {
    const s = G.createInitialState();
    assertEqual(s.score, 0, 'score');
    assertEqual(s.lines, 0, 'lines');
    assertEqual(s.status, G.GAME_STATUS.READY, 'status');
    assertEqual(s.board.length, 20, '상태 보드 행 수');
    assertEqual(s.board[0].length, 10, '상태 보드 열 수');
  });

  test('초기 상태는 호출마다 새 객체다', () => {
    const a = G.createInitialState();
    const b = G.createInitialState();
    assert(a !== b && a.board !== b.board, '상태나 보드를 공유한다');
  });

  // SPEC_01 — 시작 버튼과 첫 블록 생성

  test('createInitialState().activePiece는 null이다', () => {
    assertEqual(G.createInitialState().activePiece, null, 'activePiece');
  });

  test('TETROMINO_TYPES는 I, O, T, S, Z, J, L 7종이다', () => {
    assert(Array.isArray(G.TETROMINO_TYPES), 'TETROMINO_TYPES가 배열이 아니다');
    assertEqual(G.TETROMINO_TYPES.join(','), 'I,O,T,S,Z,J,L', 'TETROMINO_TYPES');
  });

  test('각 테트로미노는 서로 다른 4개 셀을 가진다', () => {
    G.TETROMINO_TYPES.forEach((type) => {
      const cells = G.TETROMINOES[type];
      assert(Array.isArray(cells), type + ' 정의가 없다');
      assertEqual(cells.length, 4, type + ' 셀 수');
      const keys = new Set(cells.map(([r, c]) => r + ',' + c));
      assertEqual(keys.size, 4, type + ' 서로 다른 셀 수');
    });
  });

  test('pickTetrominoType은 random 값에 따라 종류를 고른다', () => {
    assertEqual(G.pickTetrominoType(() => 0), 'I', 'random 0');
    assertEqual(G.pickTetrominoType(() => 0.999), 'L', 'random 0.999');
    G.TETROMINO_TYPES.forEach((type, i) => {
      assertEqual(G.pickTetrominoType(() => (i + 0.5) / 7), type, 'random ' + i + '번째 구간');
    });
    assert(G.TETROMINO_TYPES.includes(G.pickTetrominoType()), '인자 생략 시 유효한 종류가 아니다');
  });

  test('7종 모두 생성 위치가 0~1행, 3~6열 안에 있다', () => {
    G.TETROMINO_TYPES.forEach((type, i) => {
      const s = G.startGame(G.createInitialState(), () => (i + 0.5) / 7);
      assertEqual(s.activePiece.type, type, '생성된 종류');
      const cells = G.getPieceCells(s.activePiece);
      assertEqual(cells.length, 4, type + ' 셀 수');
      cells.forEach(([r, c]) => {
        assert(r >= 0 && r <= 1, type + ' 행 ' + r + '이 0~1 밖이다');
        assert(c >= 3 && c <= 6, type + ' 열 ' + c + '이 3~6 밖이다');
      });
    });
  });

  test('생성 위치 예: I는 0행 3~6열, O는 0~1행 4~5열', () => {
    const sort = (cells) => cells.map(([r, c]) => r + ',' + c).sort().join(' ');
    const i = G.startGame(G.createInitialState(), () => 0);
    assertEqual(sort(G.getPieceCells(i.activePiece)), '0,3 0,4 0,5 0,6', 'I 셀');
    const o = G.startGame(G.createInitialState(), () => 1.5 / 7);
    assertEqual(sort(G.getPieceCells(o.activePiece)), '0,4 0,5 1,4 1,5', 'O 셀');
  });

  test('startGame은 PLAYING 상태와 activePiece를 반환하고 보드·점수는 그대로다', () => {
    const s = G.startGame(G.createInitialState(), () => 0);
    assertEqual(s.status, G.GAME_STATUS.PLAYING, 'status');
    assert(s.activePiece && typeof s.activePiece === 'object', 'activePiece가 없다');
    assertEqual(s.score, 0, 'score');
    assertEqual(s.lines, 0, 'lines');
    assertEqual(s.board.length, 20, '보드 행 수');
    s.board.forEach((row, r) => {
      assertEqual(row.length, 10, r + '행의 셀 수');
      row.forEach((cell, c) => assertEqual(cell, 0, '셀 [' + r + '][' + c + ']'));
    });
  });

  test('startGame은 입력 상태를 수정하지 않는다', () => {
    const before = G.createInitialState();
    const after = G.startGame(before, () => 0);
    assert(after !== before, '같은 객체를 반환했다');
    assertEqual(before.status, G.GAME_STATUS.READY, '입력 status');
    assertEqual(before.activePiece, null, '입력 activePiece');
  });

  test('READY가 아닌 상태에서 startGame은 입력 상태를 그대로 반환한다', () => {
    const playing = G.startGame(G.createInitialState(), () => 0);
    assert(G.startGame(playing, () => 0.999) === playing, 'PLAYING 상태에서 새 객체를 반환했다');
    ['LANDED', 'PAUSED', 'GAME_OVER'].forEach((key) => {
      const s = { ...G.createInitialState(), status: G.GAME_STATUS[key] };
      assert(G.startGame(s) === s, key + ' 상태에서 새 객체를 반환했다');
    });
  });

  // SPEC_01 개정 — 낙하, 이동, 회전, 재시작

  const cellKey = (cells) => cells.map(([r, c]) => r + ',' + c).sort().join(' ');
  const pieceKey = (s) => cellKey(G.getPieceCells(s.activePiece));
  const randomFor = (type) => () => (G.TETROMINO_TYPES.indexOf(type) + 0.5) / 7;
  const spawn = (type) => G.startGame(G.createInitialState(), randomFor(type));
  const repeat = (s, fn, n) => {
    for (let i = 0; i < n; i++) s = fn(s);
    return s;
  };
  const landedState = () => repeat(spawn('O'), G.moveDown, 19);

  const SPAWN_CELLS = {
    I: '0,3 0,4 0,5 0,6',
    O: '0,4 0,5 1,4 1,5',
    T: '0,4 1,3 1,4 1,5',
    S: '0,4 0,5 1,3 1,4',
    Z: '0,3 0,4 1,4 1,5',
    J: '0,3 1,3 1,4 1,5',
    L: '0,5 1,3 1,4 1,5',
  };

  test('DROP_INTERVAL_MS는 700이다', () => {
    assertEqual(G.DROP_INTERVAL_MS, 700, 'DROP_INTERVAL_MS');
  });

  test('7종 생성 셀이 생성 위치 표와 일치하고 rotation은 0이다', () => {
    G.TETROMINO_TYPES.forEach((type) => {
      const s = spawn(type);
      assertEqual(s.activePiece.type, type, '생성된 종류');
      assertEqual(pieceKey(s), cellKey(SPAWN_CELLS[type].split(' ').map((k) => k.split(',').map(Number))), type + ' 셀');
      assertEqual(s.activePiece.rotation, 0, type + ' rotation');
    });
  });

  test('I는 좌우로 한 칸씩 움직이고 경계에서 같은 객체를 반환한다', () => {
    const start = spawn('I');
    let s = G.moveLeft(start);
    assertEqual(pieceKey(s), '0,2 0,3 0,4 0,5', '왼쪽 1번');
    s = repeat(start, G.moveLeft, 3);
    assertEqual(pieceKey(s), '0,0 0,1 0,2 0,3', '왼쪽 3번');
    assert(G.moveLeft(s) === s, '왼쪽 4번째에 새 객체를 반환했다');
    s = repeat(start, G.moveRight, 3);
    assertEqual(pieceKey(s), '0,6 0,7 0,8 0,9', '오른쪽 3번');
    assert(G.moveRight(s) === s, '오른쪽 4번째에 새 객체를 반환했다');
  });

  test('7종 각각 moveDown은 한 칸씩 내리고 바닥에서 LANDED가 된다', () => {
    G.TETROMINO_TYPES.forEach((type) => {
      let s = spawn(type);
      const bottom = (st) => Math.max(...G.getPieceCells(st.activePiece).map(([r]) => r));
      let steps = 0;
      while (bottom(s) < 19) {
        const before = bottom(s);
        s = G.moveDown(s);
        steps++;
        assertEqual(s.status, G.GAME_STATUS.PLAYING, type + ' ' + steps + '번째 낙하 후 status');
        assertEqual(bottom(s), before + 1, type + ' 한 칸 낙하');
        assert(steps < 30, type + ' 바닥에 닿지 않는다');
      }
      const cellsBefore = pieceKey(s);
      const landed = G.moveDown(s);
      assertEqual(landed.status, G.GAME_STATUS.LANDED, type + ' 바닥 다음 status');
      assertEqual(pieceKey(landed), cellsBefore, type + ' LANDED 셀');
    });
  });

  test('T 회전 1·2·3이 예와 같고 4번 회전하면 처음 셀로 돌아온다', () => {
    const start = spawn('T');
    const expected = ['0,4 1,4 1,5 2,4', '1,3 1,4 1,5 2,4', '0,4 1,3 1,4 2,4'];
    let s = start;
    expected.forEach((cells, i) => {
      s = G.rotateClockwise(s);
      assertEqual(s.activePiece.rotation, i + 1, 'rotation');
      assertEqual(pieceKey(s), cells, 'rotation ' + (i + 1) + ' 셀');
    });
    s = G.rotateClockwise(s);
    assertEqual(s.activePiece.rotation, 0, '4번 회전 후 rotation');
    assertEqual(pieceKey(s), pieceKey(start), '4번 회전 후 셀');
  });

  test('O는 회전해도 셀이 그대로다', () => {
    const start = spawn('O');
    let s = start;
    for (let i = 0; i < 4; i++) {
      s = G.rotateClockwise(s);
      assertEqual(pieceKey(s), pieceKey(start), 'O 회전 ' + (i + 1) + '번 후 셀');
    }
  });

  test('I는 생성 직후 회전하지 않고 한 칸 내린 뒤 (0,5)~(3,5)로 회전한다', () => {
    const start = spawn('I');
    assert(G.rotateClockwise(start) === start, '생성 직후 회전에서 새 객체를 반환했다');
    const down = G.moveDown(start);
    assertEqual(pieceKey(down), '1,3 1,4 1,5 1,6', '한 칸 내린 셀');
    assertEqual(pieceKey(G.rotateClockwise(down)), '0,5 1,5 2,5 3,5', '회전 후 셀');
  });

  test('회전 결과가 경계를 넘으면 같은 객체를 반환한다', () => {
    let s = G.rotateClockwise(spawn('T'));
    let guard = 0;
    while (G.moveLeft(s) !== s) {
      s = G.moveLeft(s);
      assert(++guard < 20, '왼쪽 끝에 닿지 않는다');
    }
    assert(G.getPieceCells(s.activePiece).some(([, c]) => c === 0), '왼쪽 끝 열에 닿지 않았다');
    assert(G.rotateClockwise(s) === s, '왼쪽 경계 회전에서 새 객체를 반환했다');

    let r = G.moveDown(spawn('I'));
    r = G.rotateClockwise(r);
    r = repeat(r, G.moveRight, 4);
    assert(G.getPieceCells(r.activePiece).every(([, c]) => c === 9), '세로 I가 오른쪽 끝에 있지 않다');
    assert(G.rotateClockwise(r) === r, '오른쪽 경계 회전에서 새 객체를 반환했다');

    const b = repeat(spawn('I'), G.moveDown, 19);
    assertEqual(b.status, G.GAME_STATUS.PLAYING, '바닥 I status');
    assertEqual(pieceKey(b), '19,3 19,4 19,5 19,6', '바닥 I 셀');
    assert(G.rotateClockwise(b) === b, '아래 경계 회전에서 새 객체를 반환했다');
  });

  test('READY, LANDED 상태에서 이동·회전 함수는 같은 객체를 반환한다', () => {
    const ready = G.createInitialState();
    const landed = landedState();
    assertEqual(landed.status, G.GAME_STATUS.LANDED, 'LANDED 준비');
    [ready, landed].forEach((s) => {
      ['moveLeft', 'moveRight', 'moveDown', 'rotateClockwise'].forEach((name) => {
        assert(G[name](s) === s, s.status + ' 상태에서 ' + name + '이 새 객체를 반환했다');
      });
    });
  });

  test('이동·회전·낙하·재시작 함수는 입력 상태를 수정하지 않는다', () => {
    const snapshot = (s) => [s.status, s.activePiece.row, s.activePiece.col, s.activePiece.rotation].join('|');
    const base = G.moveDown(spawn('T'));
    ['moveLeft', 'moveRight', 'moveDown', 'rotateClockwise'].forEach((name) => {
      const before = snapshot(base);
      const after = G[name](base);
      assert(after !== base, name + '이 이동 가능한 상태에서 같은 객체를 반환했다');
      assertEqual(snapshot(base), before, name + ' 입력 상태');
    });
    const bottomState = repeat(spawn('O'), G.moveDown, 18);
    const beforeBottom = snapshot(bottomState);
    G.moveDown(bottomState);
    assertEqual(snapshot(bottomState), beforeBottom, 'LANDED로 바뀌는 moveDown 입력 상태');
    const landed = landedState();
    const beforeLanded = snapshot(landed);
    G.restartGame(landed, randomFor('I'));
    assertEqual(snapshot(landed), beforeLanded, 'restartGame 입력 상태');
  });

  test('LANDED가 된 뒤에도 board 셀은 모두 0이다', () => {
    const landed = landedState();
    assertEqual(landed.status, G.GAME_STATUS.LANDED, 'status');
    landed.board.forEach((row, r) => row.forEach((cell, c) => assertEqual(cell, 0, '셀 [' + r + '][' + c + ']')));
  });

  test('restartGame은 LANDED에서 새 게임을 반환하고 그 밖에는 같은 객체를 반환한다', () => {
    const landed = landedState();
    G.TETROMINO_TYPES.forEach((type) => {
      const s = G.restartGame(landed, randomFor(type));
      assertEqual(s.status, G.GAME_STATUS.PLAYING, type + ' status');
      assert(s.board !== landed.board, type + ' 이전 보드 객체를 재사용했다');
      assertEqual(s.board.length, 20, '보드 행 수');
      s.board.forEach((row, r) => {
        assertEqual(row.length, 10, r + '행의 셀 수');
        row.forEach((cell, c) => assertEqual(cell, 0, '셀 [' + r + '][' + c + ']'));
      });
      assertEqual(s.score, 0, 'score');
      assertEqual(s.lines, 0, 'lines');
      assertEqual(s.activePiece.type, type, '주입한 종류');
      assertEqual(s.activePiece.rotation, 0, 'rotation');
      assertEqual(pieceKey(s), pieceKey(spawn(type)), type + ' 생성 위치');
    });
    const ready = G.createInitialState();
    assert(G.restartGame(ready) === ready, 'READY에서 새 객체를 반환했다');
    const playing = spawn('T');
    assert(G.restartGame(playing) === playing, 'PLAYING에서 새 객체를 반환했다');
  });

  // SPEC_02 — 충돌, 고정, 줄 제거, 게임 오버

  // cellsToFill: [[행, 열, 값?], ...], fullRows: [{ row, except: [비울 열...], value? }, ...]로 고정 셀을 채운 보드
  const makeBoard = (cellsToFill = [], fullRows = []) => {
    const board = G.createEmptyBoard();
    cellsToFill.forEach(([r, c, v]) => {
      board[r][c] = v || 'Z';
    });
    fullRows.forEach(({ row, except = [], value = 'Z' }) => {
      for (let c = 0; c < 10; c++) if (!except.includes(c)) board[row][c] = value;
    });
    return board;
  };
  const spawnOn = (board, type) => G.startGame({ ...G.createInitialState(), board }, randomFor(type));
  const dropUntilLanded = (s) => {
    let guard = 0;
    while (s.status === G.GAME_STATUS.PLAYING) {
      s = G.moveDown(s);
      assert(++guard < 30, '바닥에 닿지 않는다');
    }
    return s;
  };
  const filledCells = (board) => {
    const out = [];
    board.forEach((row, r) => row.forEach((v, c) => {
      if (v !== 0) out.push(r + ',' + c + '=' + v);
    }));
    return out.join(' ');
  };
  const gameOverState = () => {
    const board = makeBoard([], [{ row: 0, except: [0, 1, 2, 7, 8, 9] }, { row: 1, except: [0, 1, 2, 7, 8, 9] }]);
    const landed = { ...G.createInitialState(), board, status: G.GAME_STATUS.LANDED, activePiece: { type: 'O', row: 18, col: 3, rotation: 0 } };
    return G.lockPiece(landed, randomFor('T'));
  };

  test('canPlace: 빈 보드 생성 블록 true, 보드 밖 false, 고정 셀과 겹치면 false', () => {
    const empty = G.createEmptyBoard();
    G.TETROMINO_TYPES.forEach((type) => {
      assertEqual(G.canPlace(empty, spawn(type).activePiece), true, type + ' 빈 보드 생성');
    });
    assertEqual(G.canPlace(empty, { type: 'I', row: 0, col: 7, rotation: 0 }), false, '오른쪽 밖');
    assertEqual(G.canPlace(empty, { type: 'O', row: 19, col: 3, rotation: 0 }), false, '바닥 밖');
    assertEqual(G.canPlace(makeBoard([[0, 4]]), spawn('T').activePiece), false, '고정 셀과 겹침');
    assertEqual(G.canPlace(makeBoard([[5, 5]]), spawn('T').activePiece), true, '떨어진 고정 셀');
  });

  test('옆 칸에 고정 셀이 있으면 moveLeft/moveRight가 같은 객체를 반환한다', () => {
    const left = spawnOn(makeBoard([[1, 2]]), 'T');
    assert(G.moveLeft(left) === left, '(1,2) 고정 셀 쪽으로 moveLeft가 움직였다');
    assert(G.moveRight(left) !== left, '반대쪽 moveRight는 움직여야 한다');
    const right = spawnOn(makeBoard([[1, 6]]), 'T');
    assert(G.moveRight(right) === right, '(1,6) 고정 셀 쪽으로 moveRight가 움직였다');
  });

  test('아래 칸에 고정 셀이 있으면 moveDown이 셀을 그대로 두고 LANDED를 반환한다', () => {
    const s = spawnOn(makeBoard([[2, 4]]), 'O');
    const landed = G.moveDown(s);
    assertEqual(landed.status, G.GAME_STATUS.LANDED, 'status');
    assertEqual(pieceKey(landed), '0,4 0,5 1,4 1,5', '셀');
  });

  test('회전 결과가 고정 셀과 겹치면 rotateClockwise가 같은 객체를 반환한다', () => {
    const s = spawnOn(makeBoard([[2, 4]]), 'T');
    assert(G.rotateClockwise(s) === s, '고정 셀과 겹치는 회전이 적용됐다');
  });

  test('바닥의 O를 lockPiece하면 보드에 쓰이고 주입한 다음 블록이 생성된다', () => {
    const landed = landedState();
    const s = G.lockPiece(landed, randomFor('T'));
    assertEqual(filledCells(s.board), '18,4=O 18,5=O 19,4=O 19,5=O', '보드');
    assertEqual(s.status, G.GAME_STATUS.PLAYING, 'status');
    assertEqual(s.activePiece.type, 'T', '다음 종류');
    assertEqual(s.activePiece.rotation, 0, 'rotation');
    assertEqual(pieceKey(s), pieceKey(spawn('T')), '다음 블록 생성 위치');
    assertEqual(s.lines, 0, 'lines');
    assertEqual(s.score, 0, 'score');
  });

  test('lockPiece는 LANDED가 아니면 같은 객체를 반환하고 입력을 수정하지 않는다', () => {
    const ready = G.createInitialState();
    const playing = spawn('T');
    assert(G.lockPiece(ready) === ready, 'READY에서 새 객체를 반환했다');
    assert(G.lockPiece(playing) === playing, 'PLAYING에서 새 객체를 반환했다');
    const landed = landedState();
    const before = JSON.stringify(landed);
    const boardRef = landed.board;
    G.lockPiece(landed, randomFor('I'));
    assertEqual(JSON.stringify(landed), before, '입력 상태');
    assert(landed.board === boardRef, '입력 보드 참조가 바뀌었다');
  });

  test('한 줄 제거: 19행이 4·5열만 빈 상태에서 O를 고정하면 lines +1', () => {
    const s = dropUntilLanded(spawnOn(makeBoard([], [{ row: 19, except: [4, 5] }]), 'O'));
    assertEqual(pieceKey(s), '18,4 18,5 19,4 19,5', 'O 착지 위치');
    const locked = G.lockPiece(s, randomFor('I'));
    assertEqual(locked.lines, 1, 'lines');
    assertEqual(filledCells(locked.board), '19,4=O 19,5=O', '보드');
  });

  test('두 줄 동시 제거: 18·19행이 4·5열만 빈 상태에서 O를 고정하면 lines +2', () => {
    const board = makeBoard([], [{ row: 18, except: [4, 5] }, { row: 19, except: [4, 5] }]);
    const locked = G.lockPiece(dropUntilLanded(spawnOn(board, 'O')), randomFor('I'));
    assertEqual(locked.lines, 2, 'lines');
    assertEqual(filledCells(locked.board), '', '보드');
  });

  test('네 줄 동시 제거: 16~19행이 9열만 빈 상태에서 세로 I를 고정하면 lines +4', () => {
    const board = makeBoard([], [16, 17, 18, 19].map((row) => ({ row, except: [9] })));
    let s = G.rotateClockwise(G.moveDown(spawnOn(board, 'I')));
    s = repeat(s, G.moveRight, 4);
    assertEqual(pieceKey(s), '0,9 1,9 2,9 3,9', '세로 I 위치');
    s = dropUntilLanded(s);
    assertEqual(pieceKey(s), '16,9 17,9 18,9 19,9', '세로 I 착지');
    const locked = G.lockPiece(s, randomFor('O'));
    assertEqual(locked.lines, 4, 'lines');
    assertEqual(filledCells(locked.board), '', '보드');
  });

  test('떨어진 줄: 17·19행만 가득 찬 보드에서 2줄을 지우고 16·18행이 18·19행으로 내려온다', () => {
    const board = makeBoard([[16, 0, 'I']], [{ row: 17, value: 'L' }, { row: 18, except: [0], value: 'J' }, { row: 19, value: 'L' }]);
    const { board: next, cleared } = G.clearLines(board);
    assertEqual(cleared, 2, 'cleared');
    assertEqual(next[19].join(','), '0,J,J,J,J,J,J,J,J,J', '19행');
    assertEqual(next[18].join(','), 'I,0,0,0,0,0,0,0,0,0', '18행');
    for (let r = 0; r < 18; r++) assert(next[r].every((v) => v === 0), r + '행이 비어 있지 않다');
  });

  test('clearLines는 입력을 수정하지 않고 20×10 독립 행을 반환하며, 가득 찬 줄이 없으면 그대로다', () => {
    const board = makeBoard([[3, 3, 'T']], [{ row: 19 }]);
    const before = JSON.stringify(board);
    const { board: next } = G.clearLines(board);
    assertEqual(JSON.stringify(board), before, '입력 보드');
    assertEqual(next.length, 20, '행 수');
    next.forEach((row, r) => {
      assertEqual(row.length, 10, r + '행 셀 수');
      assert(!board.includes(row), r + '행이 입력 보드의 행을 재사용한다');
      for (let s = r + 1; s < next.length; s++) assert(row !== next[s], r + '행과 ' + s + '행이 같은 배열이다');
    });
    const partial = makeBoard([[19, 0], [5, 5, 'I']]);
    const none = G.clearLines(partial);
    assertEqual(none.cleared, 0, '가득 찬 줄 없음 cleared');
    assertEqual(JSON.stringify(none.board), JSON.stringify(partial), '가득 찬 줄 없음 내용');
  });

  test('lines는 누적되고 score는 바뀌지 않는다', () => {
    const base = { ...G.createInitialState(), board: makeBoard([], [{ row: 19, except: [4, 5] }]), lines: 3, score: 7 };
    const s = dropUntilLanded(G.startGame(base, randomFor('O')));
    const locked = G.lockPiece(s, randomFor('O'));
    assertEqual(locked.lines, 4, 'lines');
    assertEqual(locked.score, 7, 'score');
  });

  test('생성 위치가 막히면 7종 모두 GAME_OVER이고 방금 고정한 블록은 보드에 남는다', () => {
    const board = makeBoard([], [{ row: 0, except: [0, 1, 2, 7, 8, 9] }, { row: 1, except: [0, 1, 2, 7, 8, 9] }]);
    const landed = { ...G.createInitialState(), board, status: G.GAME_STATUS.LANDED, activePiece: { type: 'O', row: 18, col: 3, rotation: 0 } };
    G.TETROMINO_TYPES.forEach((type) => {
      const s = G.lockPiece(landed, randomFor(type));
      assertEqual(s.status, G.GAME_STATUS.GAME_OVER, type + ' status');
      assertEqual(s.activePiece, null, type + ' activePiece');
      assertEqual([s.board[18][4], s.board[18][5], s.board[19][4], s.board[19][5]].join(''), 'OOOO', type + ' 고정한 O');
    });
  });

  test('생성 위치 밖만 막혀 있으면 lockPiece 결과는 PLAYING이다', () => {
    const landed = { ...G.createInitialState(), board: makeBoard([[0, 0], [0, 9], [1, 0]]), status: G.GAME_STATUS.LANDED, activePiece: { type: 'O', row: 18, col: 3, rotation: 0 } };
    G.TETROMINO_TYPES.forEach((type) => {
      assertEqual(G.lockPiece(landed, randomFor(type)).status, G.GAME_STATUS.PLAYING, type + ' status');
    });
  });

  test('줄 제거로 생성 위치가 비워지면 게임 오버가 아니다', () => {
    const board = makeBoard([[2, 4], [2, 5]], [{ row: 0, except: [4, 5] }, { row: 1, except: [4, 5] }]);
    const landed = { ...G.createInitialState(), board, status: G.GAME_STATUS.LANDED, activePiece: { type: 'O', row: 0, col: 3, rotation: 0 } };
    G.TETROMINO_TYPES.forEach((type) => {
      const s = G.lockPiece(landed, randomFor(type));
      assertEqual(s.lines, 2, type + ' lines');
      assertEqual(s.status, G.GAME_STATUS.PLAYING, type + ' status');
      assertEqual(filledCells(s.board), '2,4=Z 2,5=Z', type + ' 보드');
    });
  });

  test('GAME_OVER에서 startGame, 이동·회전·낙하, lockPiece가 같은 객체를 반환한다', () => {
    const over = gameOverState();
    assertEqual(over.status, G.GAME_STATUS.GAME_OVER, 'GAME_OVER 준비');
    ['startGame', 'moveLeft', 'moveRight', 'moveDown', 'rotateClockwise', 'lockPiece'].forEach((name) => {
      assert(G[name](over, randomFor('I')) === over, name + '이 새 객체를 반환했다');
    });
  });

  test('restartGame은 GAME_OVER에서 빈 보드의 새 게임을 반환한다', () => {
    const over = { ...gameOverState(), lines: 5 };
    const s = G.restartGame(over, randomFor('S'));
    assertEqual(s.status, G.GAME_STATUS.PLAYING, 'status');
    assertEqual(filledCells(s.board), '', '보드');
    assertEqual(s.score, 0, 'score');
    assertEqual(s.lines, 0, 'lines');
    assertEqual(s.activePiece.type, 'S', '주입한 종류');
    assertEqual(pieceKey(s), pieceKey(spawn('S')), '생성 위치');
  });

  // SPEC_03 — 점수, 하드 드롭, 로컬 리더보드

  const withScore = (s, score) => ({ ...s, score });
  const fourLineBoard = () => makeBoard([], [16, 17, 18, 19].map((row) => ({ row, except: [9] })));
  const verticalIAtCol9 = (board) => repeat(G.rotateClockwise(G.moveDown(spawnOn(board, 'I'))), G.moveRight, 4);
  const entry = (id, score, playedAt, extra = {}) => ({ id, name: '이름' + id, score, clearedLines: 0, playedAt, ...extra });

  test('점수·리더보드 상수 값', () => {
    assertEqual(G.LINE_SCORES.join(','), '0,100,300,500,800', 'LINE_SCORES');
    assertEqual(G.SOFT_DROP_SCORE, 1, 'SOFT_DROP_SCORE');
    assertEqual(G.HARD_DROP_SCORE, 2, 'HARD_DROP_SCORE');
    assertEqual(G.LEADERBOARD_KEY, 'tetris-loop.leaderboard.v1', 'LEADERBOARD_KEY');
    assertEqual(G.LEADERBOARD_SIZE, 10, 'LEADERBOARD_SIZE');
  });

  test('lockAndScore는 0·1·2·4줄 제거에 0·100·300·800점을 더한다', () => {
    const cases = [
      [0, withScore(landedState(), 5)],
      [1, withScore(dropUntilLanded(spawnOn(makeBoard([], [{ row: 19, except: [4, 5] }]), 'O')), 5)],
      [2, withScore(dropUntilLanded(spawnOn(makeBoard([], [{ row: 18, except: [4, 5] }, { row: 19, except: [4, 5] }]), 'O')), 5)],
      [4, withScore(dropUntilLanded(verticalIAtCol9(fourLineBoard())), 5)],
    ];
    cases.forEach(([lines, s]) => {
      assertEqual(s.status, G.GAME_STATUS.LANDED, lines + '줄 준비');
      const next = G.lockAndScore(s, randomFor('T'));
      assertEqual(next.lines, lines, lines + '줄 lines');
      assertEqual(next.score, 5 + G.LINE_SCORES[lines], lines + '줄 score');
      assertEqual(next.status, G.GAME_STATUS.PLAYING, lines + '줄 status');
    });
  });

  test('lockAndScore는 LANDED가 아니면 같은 객체, lockPiece·moveDown은 점수를 바꾸지 않는다', () => {
    [G.createInitialState(), spawn('T'), gameOverState()].forEach((s) => {
      assert(G.lockAndScore(s) === s, s.status + '에서 lockAndScore가 새 객체를 반환했다');
    });
    const playing = withScore(spawn('O'), 5);
    assertEqual(G.moveDown(playing).score, 5, 'moveDown score');
    const landed = withScore(dropUntilLanded(spawnOn(makeBoard([], [{ row: 19, except: [4, 5] }]), 'O')), 5);
    const locked = G.lockPiece(landed, randomFor('T'));
    assertEqual(locked.lines, 1, 'lockPiece lines');
    assertEqual(locked.score, 5, 'lockPiece score');
  });

  test('softDrop은 한 칸마다 1점, 바닥에서는 LANDED와 0점, PLAYING이 아니면 같은 객체', () => {
    let s = G.softDrop(spawn('O'));
    assertEqual(s.score, 1, '1칸');
    assertEqual(pieceKey(s), '1,4 1,5 2,4 2,5', '1칸 셀');
    s = repeat(s, G.softDrop, 17);
    assertEqual(s.score, 18, '18칸');
    assertEqual(s.status, G.GAME_STATUS.PLAYING, '18칸 status');
    const bottom = G.softDrop(s);
    assertEqual(bottom.status, G.GAME_STATUS.LANDED, '바닥 status');
    assertEqual(bottom.score, 18, '바닥 score');
    assertEqual(pieceKey(bottom), pieceKey(s), '바닥 셀');
    [G.createInitialState(), bottom, gameOverState()].forEach((st) => {
      assert(G.softDrop(st) === st, st.status + '에서 softDrop이 새 객체를 반환했다');
    });
  });

  test('빈 보드의 O를 hardDrop하면 18칸 ×2 = 36점, 바닥에 고정되고 다음 블록이 나온다', () => {
    const s = G.hardDrop(spawn('O'), randomFor('T'));
    assertEqual(s.score, 36, 'score');
    assertEqual(filledCells(s.board), '18,4=O 18,5=O 19,4=O 19,5=O', '보드');
    assertEqual(s.status, G.GAME_STATUS.PLAYING, 'status');
    assertEqual(s.activePiece.type, 'T', '다음 종류');
    assertEqual(pieceKey(s), pieceKey(spawn('T')), '다음 블록 위치');
  });

  test('세로 I를 9열로 hardDrop하면 이동 칸 ×2 + 800점, lines +4', () => {
    const s = verticalIAtCol9(fourLineBoard());
    assertEqual(pieceKey(s), '0,9 1,9 2,9 3,9', '세로 I 위치');
    const next = G.hardDrop(s, randomFor('O'));
    assertEqual(next.lines, 4, 'lines');
    assertEqual(next.score, 16 * 2 + 800, 'score');
    assertEqual(filledCells(next.board), '', '보드');
  });

  test('더 내려갈 수 없는 블록을 hardDrop하면 이동 점수 0으로 고정된다', () => {
    const s = repeat(spawn('O'), G.moveDown, 18);
    assertEqual(s.status, G.GAME_STATUS.PLAYING, '준비 status');
    const next = G.hardDrop(s, randomFor('I'));
    assertEqual(next.score, 0, 'score');
    assertEqual(filledCells(next.board), '18,4=O 18,5=O 19,4=O 19,5=O', '보드');
    assertEqual(next.status, G.GAME_STATUS.PLAYING, 'status');
  });

  test('생성 위치가 막히는 고정이면 hardDrop 결과가 GAME_OVER다', () => {
    const board = makeBoard([], [{ row: 0, except: [0, 1, 2, 7, 8, 9] }, { row: 1, except: [0, 1, 2, 7, 8, 9] }]);
    const s = { ...G.createInitialState(), board, status: G.GAME_STATUS.PLAYING, activePiece: { type: 'O', row: 10, col: 0, rotation: 0 } };
    const next = G.hardDrop(s, randomFor('T'));
    assertEqual(next.status, G.GAME_STATUS.GAME_OVER, 'status');
    assertEqual(next.activePiece, null, 'activePiece');
    assertEqual(next.score, 8 * 2, 'score');
    assertEqual([next.board[18][1], next.board[18][2], next.board[19][1], next.board[19][2]].join(''), 'OOOO', '고정한 O');
  });

  test('hardDrop은 PLAYING이 아니면 같은 객체를 반환하고 입력을 수정하지 않는다', () => {
    [G.createInitialState(), landedState(), gameOverState()].forEach((s) => {
      assert(G.hardDrop(s) === s, s.status + '에서 hardDrop이 새 객체를 반환했다');
    });
    const s = spawn('T');
    const before = JSON.stringify(s);
    G.hardDrop(s, randomFor('I'));
    assertEqual(JSON.stringify(s), before, '입력 상태');
  });

  test('validateName은 trim 후 2~10자만 허용한다', () => {
    const ok = (raw, name) => {
      const r = G.validateName(raw);
      assertEqual(r.ok, true, JSON.stringify(raw) + ' ok');
      assertEqual(r.name, name, JSON.stringify(raw) + ' name');
    };
    const bad = (raw) => assertEqual(G.validateName(raw).ok, false, JSON.stringify(raw) + ' 거부');
    ok('  별님  ', '별님');
    ok('가나', '가나');
    ok('ab', 'ab');
    ok('abcdefghij', 'abcdefghij');
    ok('  abcdefghij  ', 'abcdefghij');
    ok('a b', 'a b');
    bad('a');
    bad('가');
    bad('');
    bad('   ');
    bad('abcdefghijk');
  });

  test('addLeaderboardEntry는 점수 내림차순·동점은 이른 기록 먼저로 정렬하고 입력을 수정하지 않는다', () => {
    const list = [entry('a', 100, '2026-01-01T00:00:00.000Z'), entry('b', 300, '2026-01-02T00:00:00.000Z')];
    const before = JSON.stringify(list);
    const next = G.addLeaderboardEntry(list, entry('c', 200, '2026-01-03T00:00:00.000Z'));
    assertEqual(next.map((e) => e.id).join(','), 'b,c,a', '정렬');
    assertEqual(JSON.stringify(list), before, '입력 배열');
    assert(next !== list, '입력 배열을 그대로 반환했다');
    const tie = G.addLeaderboardEntry(next, entry('d', 200, '2026-01-01T12:00:00.000Z'));
    assertEqual(tie.map((e) => e.id).join(','), 'b,d,c,a', '동점은 이른 기록 먼저');
  });

  test('addLeaderboardEntry는 10개만 남기고, 순위 밖 점수는 목록을 바꾸지 않는다', () => {
    const full = Array.from({ length: 10 }, (_, i) => entry('e' + i, 1000 - i * 100, '2026-01-01T00:00:0' + i + '.000Z'));
    const low = entry('low', 50, '2026-02-01T00:00:00.000Z');
    const same = G.addLeaderboardEntry(full, low);
    assertEqual(same.length, 10, '순위 밖 길이');
    assert(!same.includes(low), '순위 밖 항목이 들어갔다');
    assertEqual(same.map((e) => e.id).join(','), full.map((e) => e.id).join(','), '순위 밖 목록');
    const mid = entry('mid', 150, '2026-02-01T00:00:00.000Z');
    const cut = G.addLeaderboardEntry(full, mid);
    assertEqual(cut.length, 10, '11개 → 10개');
    assert(cut.includes(mid), '새 항목이 없다');
    assert(!cut.some((e) => e.id === 'e9'), '가장 낮은 항목이 남았다');
  });

  test('parseLeaderboard는 손상 입력을 빈 목록으로, 틀린 항목은 버리고, 10개만 정렬해 반환한다', () => {
    [null, undefined, '{broken', '{}', '42', '"text"'].forEach((t) => {
      const r = G.parseLeaderboard(t);
      assert(Array.isArray(r) && r.length === 0, String(t) + ' → 빈 목록이 아니다');
    });
    const mixed = [
      entry('ok1', 100, '2026-01-01T00:00:00.000Z'),
      { name: '아이디없음', score: 1, clearedLines: 0, playedAt: 'x' },
      entry('str', '200', '2026-01-01T00:00:00.000Z'),
      entry('short', 300, '2026-01-01T00:00:00.000Z', { name: 'a' }),
      null,
      entry('ok2', 400, '2026-01-01T00:00:00.000Z', { extra: true }),
    ];
    const parsed = G.parseLeaderboard(JSON.stringify(mixed));
    assertEqual(parsed.map((e) => e.id).join(','), 'ok2,ok1', '유효 항목만');
    assertEqual(Object.keys(parsed[0]).sort().join(','), 'clearedLines,id,name,playedAt,score', '항목 필드');
    const twelve = Array.from({ length: 12 }, (_, i) => entry('t' + i, (i * 37) % 12, '2026-01-01T00:00:' + String(10 + i) + '.000Z'));
    const top = G.parseLeaderboard(JSON.stringify(twelve));
    assertEqual(top.length, 10, '12개 → 10개');
    for (let i = 1; i < top.length; i++) assert(top[i - 1].score >= top[i].score, '정렬되지 않았다');
    assertEqual(JSON.stringify(G.parseLeaderboard(G.serializeLeaderboard(top))), JSON.stringify(top), '직렬화 왕복');
  });

  // SPEC_04 — 레벨, 속도, 다음 블록, 일시정지

  test('레벨·속도 상수 값', () => {
    assertEqual(G.LEVEL_LINES, 10, 'LEVEL_LINES');
    assertEqual(G.MIN_DROP_INTERVAL_MS, 100, 'MIN_DROP_INTERVAL_MS');
    assertEqual(G.DROP_INTERVAL_STEP_MS, 60, 'DROP_INTERVAL_STEP_MS');
  });

  test('getLevel: 줄 0·9·10·19·20·100 → 1·1·2·2·3·11', () => {
    [[0, 1], [9, 1], [10, 2], [19, 2], [20, 3], [100, 11]].forEach(([lines, level]) => {
      assertEqual(G.getLevel(lines), level, '줄 ' + lines);
    });
  });

  test('getDropInterval: 레벨 1·2·10·11·12·30 → 700·640·160·100·100·100, 기준 간격은 700 유지', () => {
    [[1, 700], [2, 640], [10, 160], [11, 100], [12, 100], [30, 100]].forEach(([level, ms]) => {
      assertEqual(G.getDropInterval(level), ms, '레벨 ' + level);
    });
    assertEqual(G.DROP_INTERVAL_MS, 700, 'DROP_INTERVAL_MS');
    assertEqual(G.getDropInterval(G.getLevel(9)), 700, '줄 9 간격');
    assertEqual(G.getDropInterval(G.getLevel(10)), 640, '줄 10 간격');
  });

  test('togglePause는 PLAYING ↔ PAUSED만 오가고 다른 필드와 입력을 바꾸지 않는다', () => {
    const playing = { ...spawn('T'), score: 7, lines: 3 };
    const before = JSON.stringify(playing);
    const paused = G.togglePause(playing);
    assertEqual(paused.status, G.GAME_STATUS.PAUSED, 'PLAYING → PAUSED');
    assert(paused !== playing, '같은 객체를 반환했다');
    assert(paused.board === playing.board, '보드가 바뀌었다');
    assertEqual(paused.score, 7, 'score');
    assertEqual(paused.lines, 3, 'lines');
    assertEqual(JSON.stringify(paused.activePiece), JSON.stringify(playing.activePiece), 'activePiece');
    assertEqual(JSON.stringify(playing), before, '입력 상태');
    const resumed = G.togglePause(paused);
    assertEqual(resumed.status, G.GAME_STATUS.PLAYING, 'PAUSED → PLAYING');
    assertEqual(paused.status, G.GAME_STATUS.PAUSED, 'PAUSED 입력 상태');
    [G.createInitialState(), landedState(), gameOverState()].forEach((s) => {
      assert(G.togglePause(s) === s, s.status + '에서 togglePause가 새 객체를 반환했다');
    });
  });

  test('PAUSED에서 이동·회전·낙하·드롭·고정·시작·재시작 함수 10개가 같은 객체를 반환한다', () => {
    const paused = G.togglePause(spawn('T'));
    ['moveLeft', 'moveRight', 'moveDown', 'softDrop', 'rotateClockwise', 'hardDrop', 'lockAndScore', 'lockPiece', 'startGame', 'restartGame'].forEach((name) => {
      assert(G[name](paused, randomFor('I')) === paused, name + '이 새 객체를 반환했다');
    });
  });

  test('randomForType으로 주입하면 7종 모두 그 종류가 새 블록이 된다', () => {
    G.TETROMINO_TYPES.forEach((type) => {
      assertEqual(G.pickTetrominoType(G.randomForType(type)), type, type + ' pickTetrominoType');
      assertEqual(G.startGame(G.createInitialState(), G.randomForType(type)).activePiece.type, type, type + ' startGame');
      assertEqual(G.lockAndScore(landedState(), G.randomForType(type)).activePiece.type, type, type + ' lockAndScore');
      assertEqual(G.hardDrop(spawn('O'), G.randomForType(type)).activePiece.type, type, type + ' hardDrop');
    });
  });

  // SPEC_05 — 고스트 블록과 홀드

  const ghostOf = (board, piece) => ({ ...piece, row: G.calculateGhostY(board, piece) });

  test('createInitialState의 holdType은 null, holdUsed는 false다', () => {
    const s = G.createInitialState();
    assertEqual(s.holdType, null, 'holdType');
    assertEqual(s.holdUsed, false, 'holdUsed');
  });

  test('calculateGhostY fixture: 빈 보드 O·I → 18, (10,4) 위 T → 8, 바닥 블록 → 그 row, 입력 불변', () => {
    const empty = G.createEmptyBoard();
    assertEqual(G.calculateGhostY(empty, spawn('O').activePiece), 18, '빈 보드 O');
    const i = spawn('I').activePiece;
    assertEqual(G.calculateGhostY(empty, i), 18, '빈 보드 I');
    assertEqual(cellKey(G.getPieceCells(ghostOf(empty, i))), '19,3 19,4 19,5 19,6', 'I 고스트 셀');
    const t = spawnOn(makeBoard([[10, 4]]), 'T');
    assertEqual(G.calculateGhostY(t.board, t.activePiece), 8, '(10,4) 위 T');
    const resting = repeat(spawn('O'), G.moveDown, 18);
    assertEqual(G.calculateGhostY(resting.board, resting.activePiece), resting.activePiece.row, '바닥 블록');
    const before = JSON.stringify(t.activePiece);
    G.calculateGhostY(t.board, t.activePiece);
    assertEqual(JSON.stringify(t.activePiece), before, '입력 블록');
  });

  test('7종 모두 고스트 셀과 hardDrop으로 고정된 셀이 같다', () => {
    const board = makeBoard([[15, 3], [17, 5], [12, 4], [18, 8]]);
    G.TETROMINO_TYPES.forEach((type) => {
      const s = spawnOn(board, type);
      const ghostCells = G.getPieceCells(ghostOf(s.board, s.activePiece));
      const dropped = G.hardDrop(s, randomFor('O'));
      ghostCells.forEach(([r, c]) => {
        assertEqual(s.board[r][c], 0, type + ' 고스트 칸이 비어 있지 않다 ' + r + ',' + c);
        assertEqual(dropped.board[r][c], type, type + ' 고정 칸 ' + r + ',' + c);
      });
    });
  });

  test('빈 홀드에서 holdPiece: 현재 종류를 보관하고 주입한 종류가 생성 위치에 나온다', () => {
    const s = { ...spawn('T'), score: 12, lines: 3 };
    const h = G.holdPiece(s, randomFor('L'));
    assertEqual(h.holdType, 'T', 'holdType');
    assertEqual(h.holdUsed, true, 'holdUsed');
    assertEqual(h.activePiece.type, 'L', '새 블록 종류');
    assertEqual(h.activePiece.rotation, 0, 'rotation');
    assertEqual(pieceKey(h), pieceKey(spawn('L')), '생성 위치');
    assertEqual(h.status, G.GAME_STATUS.PLAYING, 'status');
    assertEqual(h.score, 12, 'score');
    assertEqual(h.lines, 3, 'lines');
  });

  test('holdUsed가 true면 holdPiece가 같은 객체를 반환한다', () => {
    const h = G.holdPiece(spawn('T'), randomFor('L'));
    assert(G.holdPiece(h, randomFor('O')) === h, '두 번째 홀드에서 새 객체를 반환했다');
  });

  test('고정 후 holdUsed가 false가 되고, 다시 홀드하면 생성 위치·회전 0으로 교환된다', () => {
    assertEqual(G.lockPiece({ ...landedState(), holdUsed: true }, randomFor('I')).holdUsed, false, 'lockPiece 후');
    assertEqual(G.lockAndScore({ ...landedState(), holdUsed: true }, randomFor('I')).holdUsed, false, 'lockAndScore 후');
    const held = G.holdPiece(spawn('T'), randomFor('O'));
    const locked = G.hardDrop(held, randomFor('S'));
    assertEqual(locked.holdUsed, false, 'hardDrop 후');
    assertEqual(locked.holdType, 'T', '홀드 유지');
    const moved = G.rotateClockwise(G.moveLeft(G.moveDown(locked)));
    assertEqual(moved.activePiece.rotation, 1, '돌린 뒤 rotation');
    const swapped = G.holdPiece(moved, randomFor('Z'));
    assertEqual(swapped.activePiece.type, 'T', '꺼낸 종류');
    assertEqual(swapped.activePiece.rotation, 0, '꺼낸 rotation');
    assertEqual(pieceKey(swapped), pieceKey(spawn('T')), '꺼낸 블록 생성 위치');
    assertEqual(swapped.holdType, 'S', '새로 보관한 종류');
    assertEqual(swapped.holdUsed, true, 'holdUsed');
  });

  test('READY·LANDED·PAUSED·GAME_OVER에서 holdPiece는 같은 객체이고, 입력을 수정하지 않는다', () => {
    [G.createInitialState(), landedState(), G.togglePause(spawn('T')), gameOverState()].forEach((s) => {
      assert(G.holdPiece(s, randomFor('I')) === s, s.status + '에서 holdPiece가 새 객체를 반환했다');
    });
    const s = spawn('J');
    const before = JSON.stringify(s);
    G.holdPiece(s, randomFor('I'));
    assertEqual(JSON.stringify(s), before, '입력 상태');
  });

  test('홀드로 나올 생성 자리가 막혀 있으면 GAME_OVER다', () => {
    const board = makeBoard([], [{ row: 0, except: [0, 1, 2, 7, 8, 9] }, { row: 1, except: [0, 1, 2, 7, 8, 9] }]);
    const s = { ...G.createInitialState(), board, status: G.GAME_STATUS.PLAYING, activePiece: { type: 'O', row: 10, col: 0, rotation: 0 } };
    const h = G.holdPiece(s, randomFor('T'));
    assertEqual(h.status, G.GAME_STATUS.GAME_OVER, 'status');
    assertEqual(h.activePiece, null, 'activePiece');
    assertEqual(h.holdType, 'O', 'holdType');
  });

  test('restartGame은 홀드를 비운다', () => {
    const over = { ...gameOverState(), holdType: 'T', holdUsed: true };
    const s = G.restartGame(over, randomFor('I'));
    assertEqual(s.holdType, null, 'holdType');
    assertEqual(s.holdUsed, false, 'holdUsed');
  });

  const passed = results.filter((r) => r.ok).length;
  const failed = results.length - passed;
  globalThis.__testResults = { passed, failed, results };

  if (typeof document !== 'undefined') {
    const summary = document.getElementById('summary');
    const list = document.getElementById('results');
    summary.textContent = '통과 ' + passed + ' · 실패 ' + failed;
    summary.className = failed === 0 ? 'pass' : 'fail';
    results.forEach((r) => {
      const li = document.createElement('li');
      li.className = r.ok ? 'pass' : 'fail';
      li.textContent = (r.ok ? '통과: ' : '실패: ') + r.name + (r.ok ? '' : ' — ' + r.reason);
      list.appendChild(li);
    });
  }
})();
