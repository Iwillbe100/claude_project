// 삼성 SW 역량테스트 B형(Python) 연습 서버. 외부 패키지 없이 Node 기본 모듈만 사용한다.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { judge, PYTHON } = require('./judge');

const PORT = Number(process.env.PORT) || 3000;
const HOST = '127.0.0.1'; // 사용자 코드를 실행하므로 내 컴퓨터에서만 접속 가능하게 한다.
const ROOT = __dirname;
const PROBLEM_DIR = path.join(ROOT, 'problems');
const PUBLIC_DIR = path.join(ROOT, 'public');
const SUBMISSION_FILE = path.join(ROOT, 'data', 'submissions.json');

function loadProblems() {
  const list = {};
  for (const id of fs.readdirSync(PROBLEM_DIR)) {
    const dir = path.join(PROBLEM_DIR, id);
    const metaFile = path.join(dir, 'problem.json');
    if (!fs.existsSync(metaFile)) continue;
    list[id] = { id, dir, ...JSON.parse(fs.readFileSync(metaFile, 'utf8')) };
  }
  return list;
}
const problems = loadProblems();

const LESSON_DIR = path.join(ROOT, 'lessons');
const lessons = JSON.parse(fs.readFileSync(path.join(LESSON_DIR, 'index.json'), 'utf8'));
const lessonById = Object.fromEntries(lessons.map((l) => [l.id, l]));
const practice = JSON.parse(fs.readFileSync(path.join(LESSON_DIR, 'practice.json'), 'utf8'));
const practiceFor = (lessonId) => ({
  items: practice.items[lessonId] || [],
  note: (practice.note && practice.note[lessonId]) || null,
});

function loadSubmissions() {
  try {
    return JSON.parse(fs.readFileSync(SUBMISSION_FILE, 'utf8'));
  } catch {
    return [];
  }
}
let submissions = loadSubmissions();
function saveSubmissions() {
  fs.mkdirSync(path.dirname(SUBMISSION_FILE), { recursive: true });
  fs.writeFileSync(SUBMISSION_FILE, JSON.stringify(submissions, null, 1));
}

function readText(id, file) {
  return fs.readFileSync(path.join(problems[id].dir, file), 'utf8');
}

function send(res, status, body, type = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  res.end(type.startsWith('application/json') ? JSON.stringify(body) : body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 2 << 20) {
        reject(new Error('요청이 너무 큽니다.'));
        req.destroy();
      }
    });
    req.on('end', () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
  });
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml' };
function serveStatic(req, res, pathname) {
  const file = path.normalize(path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname));
  if (!file.startsWith(PUBLIC_DIR) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    return send(res, 404, 'Not found', 'text/plain; charset=utf-8');
  }
  send(res, 200, fs.readFileSync(file), MIME[path.extname(file)] || 'application/octet-stream');
}

function problemSummary(p) {
  const mine = submissions.filter((s) => s.problemId === p.id);
  const best = mine.reduce((m, s) => Math.max(m, s.score), -1);
  return {
    id: p.id,
    title: p.title,
    category: p.category,
    difficulty: p.difficulty,
    timeLimit: p.timeLimit,
    order: p.order,
    status: mine.some((s) => s.verdict === 'AC') ? 'AC' : mine.length ? 'TRIED' : null,
    best: best < 0 ? null : best,
    attempts: mine.length,
  };
}

async function handleApi(req, res, parts, query) {
  // GET /api/problems
  if (parts.length === 1 && parts[0] === 'problems') {
    const list = Object.values(problems).map(problemSummary).sort((a, b) => a.order - b.order);
    return send(res, 200, list);
  }

  // GET /api/lessons, /api/lessons/:id
  if (parts[0] === 'lessons') {
    if (parts.length === 1) return send(res, 200, lessons);
    const lesson = lessonById[parts[1]];
    if (parts[1] === 'practice') {
      const groups = lessons
        .filter((l) => (practice.items[l.id] || []).length)
        .map((l) => ({ lessonId: l.id, title: l.title, ...practiceFor(l.id) }));
      return send(res, 200, { intro: practice.intro, groups });
    }
    if (!lesson) return send(res, 404, { error: '강의를 찾을 수 없습니다.' });
    const problem = problems[lesson.problem];
    return send(res, 200, {
      ...lesson,
      problemTitle: problem ? problem.title : null,
      practice: { intro: practice.intro, ...practiceFor(lesson.id) },
      html: fs.readFileSync(path.join(LESSON_DIR, `${lesson.id}.html`), 'utf8'),
    });
  }

  if (parts[0] === 'submissions' && parts.length === 1) {
    const pid = query.get('problem');
    const list = submissions.filter((s) => !pid || s.problemId === pid).slice().reverse();
    return send(res, 200, list);
  }

  if (parts[0] !== 'problems' || !problems[parts[1]]) return send(res, 404, { error: '문제를 찾을 수 없습니다.' });
  const p = problems[parts[1]];
  const action = parts[2];

  if (!action && req.method === 'GET') {
    return send(res, 200, {
      ...problemSummary(p),
      hints: p.hints || [],
      lesson: p.lesson || null,
      lessonTitle: p.lesson && lessonById[p.lesson] ? lessonById[p.lesson].title : null,
      practice: p.lesson ? { intro: practice.intro, ...practiceFor(p.lesson) } : null,
      statement: readText(p.id, 'statement.html'),
      template: readText(p.id, 'template.py'),
      main: readText(p.id, 'main.py'),
      sample: readText(p.id, 'tests/sample.txt'),
    });
  }

  if (action === 'solution' && req.method === 'GET') {
    if (!submissions.some((s) => s.problemId === p.id && s.verdict === 'AC')) {
      return send(res, 403, { error: '이 문제를 맞힌 뒤에 모범 답안을 볼 수 있습니다.' });
    }
    return send(res, 200, { code: readText(p.id, 'solution.py') });
  }

  if ((action === 'run' || action === 'submit') && req.method === 'POST') {
    const body = await readBody(req);
    const code = String(body.code || '');
    if (!code.trim()) return send(res, 400, { error: '코드가 비어 있습니다.' });

    if (action === 'run') {
      const custom = typeof body.input === 'string' && body.input.trim();
      const result = await judge(p, code, custom ? 'custom' : 'sample', body.input);
      return send(res, 200, { mode: custom ? 'custom' : 'sample', ...result });
    }

    const result = await judge(p, code, 'test');
    const record = {
      id: submissions.length + 1,
      problemId: p.id,
      title: p.title,
      at: new Date().toISOString(),
      verdict: result.verdict,
      score: result.score,
      timeMs: result.timeMs,
      code,
    };
    submissions.push(record);
    saveSubmissions();
    return send(res, 200, { mode: 'submit', submissionId: record.id, ...result });
  }

  send(res, 404, { error: '잘못된 요청입니다.' });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  try {
    if (url.pathname.startsWith('/api/')) {
      const parts = url.pathname.slice(5).split('/').filter(Boolean).map(decodeURIComponent);
      return await handleApi(req, res, parts, url.searchParams);
    }
    serveStatic(req, res, decodeURIComponent(url.pathname));
  } catch (err) {
    console.error(err);
    send(res, 500, { error: String(err.message || err) });
  }
});

let pyVersion = '알 수 없음';
try {
  pyVersion = execFileSync(PYTHON, ['--version'], { encoding: 'utf8' }).trim();
} catch {
  console.warn(`경고: '${PYTHON}'을 실행할 수 없습니다. PYTHON 환경변수로 경로를 지정하세요.`);
}

server.listen(PORT, HOST, () => {
  console.log(`SW B형 연습 사이트: http://localhost:${PORT}  (${pyVersion})`);
});
