// Python 채점기: 문제의 main.py와 사용자 코드(solution.py)를 임시 폴더에 두고 실행한다.
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PYTHON = process.env.PYTHON || 'python';
const OUTPUT_LIMIT = 1 << 20;

// 한 번에 하나씩 채점해서 실행 시간이 서로 영향을 주지 않게 한다.
let queue = Promise.resolve();
function enqueue(task) {
  const result = queue.then(task, task);
  queue = result.catch(() => {});
  return result;
}

function execute(dir, input, timeLimitSec) {
  return new Promise((resolve) => {
    const started = process.hrtime.bigint();
    const child = spawn(PYTHON, ['-X', 'utf8', 'main.py'], {
      cwd: dir,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONIOENCODING: 'utf-8' },
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeLimitSec * 1000);

    child.stdout.on('data', (d) => { if (stdout.length < OUTPUT_LIMIT) stdout += d; });
    child.stderr.on('data', (d) => { if (stderr.length < OUTPUT_LIMIT) stderr += d; });
    child.stdin.on('error', () => {}); // 프로그램이 입력을 다 읽기 전에 종료된 경우
    child.on('error', (err) => { stderr += String(err); });
    child.on('close', (code) => {
      clearTimeout(timer);
      const timeMs = Number(process.hrtime.bigint() - started) / 1e6;
      resolve({ code, stdout, stderr: stderr.split(dir + path.sep).join(''), timedOut, timeMs: Math.round(timeMs) });
    });

    child.stdin.end(input);
  });
}

// main.py 출력("#1 100")을 테스트 케이스별 점수로 해석한다.
function grade(input, run) {
  const [T, MARK] = input.slice(0, 64).trim().split(/\s+/).map(Number);
  const scores = {};
  const extra = [];
  for (const line of run.stdout.split(/\r?\n/)) {
    const m = /^#(\d+) (-?\d+)$/.exec(line.trim());
    if (m) scores[m[1]] = Number(m[2]);
    else if (line.trim()) extra.push(line);
  }
  const cases = [];
  let earned = 0;
  for (let tc = 1; tc <= T; tc++) {
    const s = scores[tc];
    cases.push({ tc, score: s === undefined ? null : s, mark: MARK });
    if (s === MARK) earned++;
  }

  let verdict;
  if (run.timedOut) verdict = 'TLE';
  else if (run.code !== 0) verdict = 'RE';
  else if (earned === T) verdict = 'AC';
  else verdict = 'WA';

  return {
    verdict,
    score: Math.round((earned / T) * 100),
    passed: earned,
    total: T,
    cases,
    timeMs: run.timeMs,
    stdout: extra.join('\n').slice(0, 20000),
    stderr: run.stderr.slice(-8000),
  };
}

// mode: 'sample' | 'test' | 'custom'
function judge(problem, code, mode, customInput) {
  return enqueue(async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'swb-'));
    try {
      fs.copyFileSync(path.join(problem.dir, 'main.py'), path.join(dir, 'main.py'));
      fs.writeFileSync(path.join(dir, 'solution.py'), code);

      if (mode === 'custom') {
        const run = await execute(dir, customInput, problem.timeLimit);
        return {
          verdict: run.timedOut ? 'TLE' : run.code !== 0 ? 'RE' : 'DONE',
          timeMs: run.timeMs,
          stdout: run.stdout.slice(0, 20000),
          stderr: run.stderr.slice(-8000),
        };
      }

      const file = mode === 'sample' ? 'sample.txt' : 'test.txt';
      const input = fs.readFileSync(path.join(problem.dir, 'tests', file), 'utf8');
      const run = await execute(dir, input, problem.timeLimit);
      return grade(input, run);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
}

module.exports = { judge, PYTHON };
