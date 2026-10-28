(() => {
  const app = document.getElementById('app');
  const EXAM_MS = 4 * 60 * 60 * 1000; // B형 시험 시간 4시간
  const VERDICT = { AC: '맞았습니다', WA: '틀렸습니다', TLE: '시간 초과', RE: '런타임 에러', DONE: '실행 완료' };

  const store = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, v) { try { localStorage.setItem(key, v); } catch { /* 저장 불가 환경 */ } },
    del(key) { try { localStorage.removeItem(key); } catch { /* 저장 불가 환경 */ } },
  };

  async function api(url, options = {}) {
    const res = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw Object.assign(new Error(data.error || res.statusText), { status: res.status });
    return data;
  }

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const stars = (n) => '★'.repeat(n) + '☆'.repeat(Math.max(0, 3 - n));
  const fmtTime = (iso) => new Date(iso).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  const mount = (id) => { app.replaceChildren(document.getElementById(id).content.cloneNode(true)); };

  let view = null; // 현재 화면 정리 함수 등

  // ------------------------------------------------------------ 라우터
  function route() {
    if (view && view.leave) view.leave();
    view = null;
    const hash = location.hash.slice(1) || '/';
    const parts = hash.split('/').filter(Boolean);
    document.querySelectorAll('[data-nav]').forEach((a) => {
      a.classList.toggle('active', (parts[0] || 'home') === a.dataset.nav || (parts[0] === 'p' && a.dataset.nav === 'home'));
    });
    if (parts[0] === 'p' && parts[1]) return showProblem(parts[1]);
    if (parts[0] === 'submissions') return showSubmissions();
    if (parts[0] === 'learn') return parts[1] ? showLesson(parts[1]) : showLessons();
    showHome();
  }
  window.addEventListener('hashchange', route);

  // ------------------------------------------------------------ 문제 목록
  async function showHome() {
    mount('tpl-home');
    const list = await api('/api/problems');
    const solved = list.filter((p) => p.status === 'AC').length;
    const attempts = list.reduce((s, p) => s + p.attempts, 0);
    document.getElementById('stats').innerHTML = `
      <div class="stat"><div class="v">${solved} / ${list.length}</div><div class="k">해결한 문제</div></div>
      <div class="stat"><div class="v">${attempts}</div><div class="k">총 제출</div></div>`;
    document.getElementById('problemGrid').innerHTML = list.map((p, i) => `
      <a class="card" href="#/p/${esc(p.id)}">
        <div class="no">문제 ${i + 1}</div>
        <h3>${esc(p.title)}</h3>
        <div class="row">
          <span class="chip">${esc(p.category)}</span>
          <span class="stars" title="난이도">${stars(p.difficulty)}</span>
          <span>제한 ${p.timeLimit}초</span>
          ${p.status ? `<span class="status ${p.status}">${p.status === 'AC' ? '해결' : `시도 · 최고 ${p.best}점`}</span>` : ''}
        </div>
      </a>`).join('');
  }

  // ------------------------------------------------------------ 문제 풀이 화면
  async function showProblem(id) {
    mount('tpl-problem');
    let p;
    try {
      p = await api(`/api/problems/${encodeURIComponent(id)}`);
    } catch (e) {
      app.innerHTML = `<section class="home"><p>${esc(e.message)}</p><a href="#/">목록으로</a></section>`;
      return;
    }
    const codeKey = `code:${id}`;
    document.getElementById('pTitle').textContent = p.title;
    document.getElementById('pMeta').innerHTML = `
      <span class="chip">${esc(p.category)}</span>
      <span class="stars">${stars(p.difficulty)}</span>
      <span>시간 제한 ${p.timeLimit}초 (전체 테스트 케이스 합계)</span>
      ${p.status === 'AC' ? '<span class="status AC">해결</span>' : ''}`;

    // 에디터
    const textarea = document.getElementById('editor');
    textarea.value = store.get(codeKey) ?? p.template;
    let editor;
    if (window.CodeMirror) {
      const cm = CodeMirror.fromTextArea(textarea, {
        mode: 'python',
        theme: 'material-darker',
        lineNumbers: true,
        indentUnit: 4,
        tabSize: 4,
        indentWithTabs: false,
        matchBrackets: true,
        autoCloseBrackets: true,
        extraKeys: {
          Tab: (c) => (c.somethingSelected() ? c.indentSelection('add') : c.replaceSelection('    ')),
          'Shift-Tab': (c) => c.indentSelection('subtract'),
          'Ctrl-/': 'toggleComment',
          'Cmd-/': 'toggleComment',
        },
      });
      cm.on('change', () => store.set(codeKey, cm.getValue()));
      editor = { get: () => cm.getValue(), set: (v) => cm.setValue(v), focus: () => cm.focus() };
      setTimeout(() => cm.refresh(), 0);
    } else {
      // CDN을 불러오지 못한 경우: 기본 textarea로 동작
      textarea.addEventListener('input', () => store.set(codeKey, textarea.value));
      textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
          e.preventDefault();
          textarea.setRangeText('    ', textarea.selectionStart, textarea.selectionEnd, 'end');
        }
      });
      editor = { get: () => textarea.value, set: (v) => { textarea.value = v; }, focus: () => textarea.focus() };
    }

    // 왼쪽 탭
    const leftBody = document.getElementById('leftBody');
    const tabs = {
      statement: () => { leftBody.innerHTML = `<div class="statement">${p.statement}</div>`; },
      main: () => {
        leftBody.innerHTML = `<p class="note">채점에 쓰이는 main.py입니다. 내 코드는 <code>solution.py</code>로 저장되어 이 파일에서 import됩니다. 표준 입출력은 main.py가 처리하므로 solution.py에서는 함수만 구현하면 됩니다.</p>
          <pre class="codeview">${esc(p.main)}</pre>`;
      },
      sample: () => {
        leftBody.innerHTML = `<p class="note">첫 줄은 <code>T MARK</code>(테스트 케이스 수, 배점)입니다. 각 명령 줄의 마지막 값이 기대하는 반환값입니다.<br>제출하면 더 큰 숨은 테스트 케이스 10개로 채점합니다.</p>
          <pre class="codeview">${esc(p.sample)}</pre>`;
      },
      hint: () => {
        const key = `hints:${id}`;
        const hints = p.hints || [];
        let shown = Math.min(Number(store.get(key)) || 0, hints.length);
        const draw = () => {
          if (!hints.length) {
            leftBody.innerHTML = '<p class="note">이 문제에는 아직 힌트가 없습니다.</p>';
            return;
          }
          leftBody.innerHTML = `
            <p class="note">막힌 부분만 보도록 힌트는 한 단계씩 열립니다. 힌트를 볼수록 정답에 가까워집니다. 먼저 스스로 5~10분 고민해 보세요.</p>
            ${hints.slice(0, shown).map((h, i) => `<div class="hint-card"><div class="hint-no">힌트 ${i + 1} / ${hints.length}</div>${esc(h)}</div>`).join('')}
            ${shown < hints.length
              ? `<button class="btn" id="nextHint">힌트 ${shown + 1} 보기</button>`
              : `<p class="note">힌트를 모두 열었습니다.${p.lesson ? ` 그래도 어렵다면 <b>학습</b> 탭의 강의를 읽어 보세요.` : ''}</p>`}
            ${shown ? '<button class="btn ghost small" id="resetHint" style="margin-left:8px">힌트 다시 가리기</button>' : ''}`;
          const next = document.getElementById('nextHint');
          if (next) next.onclick = () => { shown++; store.set(key, String(shown)); draw(); };
          const reset = document.getElementById('resetHint');
          if (reset) reset.onclick = () => { shown = 0; store.set(key, '0'); draw(); };
        };
        draw();
      },
      lesson: () => {
        leftBody.innerHTML = p.lesson
          ? `<p class="note">이 문제에서 쓰는 알고리즘을 설명하는 강의입니다.</p>
             <a class="lesson-link" href="#/learn/${esc(p.lesson)}"><strong>${esc(p.lessonTitle || p.lesson)}</strong><span>강의 읽으러 가기 →</span></a>
             <p class="note">파이썬 문법이나 시험 요령이 낯설다면 <a href="#/learn/python-tools">파이썬 도구함</a>과 <a href="#/learn/guide">B형 시험 가이드</a>도 보세요.</p>
             ${p.practice && p.practice.items.length ? `<h3 class="side-h">비슷한 유형의 외부 문제</h3>${practiceHtml(p.practice)}` : ''}`
          : '<p class="note">연결된 강의가 없습니다.</p>';
      },
      history: async () => {
        leftBody.innerHTML = '<p class="note"><span class="spinner"></span>불러오는 중</p>';
        const subs = await api(`/api/submissions?problem=${encodeURIComponent(id)}`);
        leftBody.innerHTML = subs.length
          ? `<table class="table" style="margin-top:16px"><thead><tr><th>#</th><th>결과</th><th>점수</th><th>시간</th><th>시각</th><th></th></tr></thead><tbody>
              ${subs.map((s) => `<tr><td>${s.id}</td><td class="v v-${s.verdict}">${VERDICT[s.verdict]}</td><td>${s.score}</td><td>${s.timeMs}ms</td><td>${fmtTime(s.at)}</td>
              <td><button class="btn ghost small" data-sub="${s.id}">코드</button></td></tr>`).join('')}</tbody></table>`
          : '<p class="note">아직 제출 기록이 없습니다.</p>';
        leftBody.querySelectorAll('[data-sub]').forEach((b) => {
          b.onclick = () => openCode(subs.find((s) => String(s.id) === b.dataset.sub));
        });
      },
      solution: async () => {
        try {
          const { code } = await api(`/api/problems/${encodeURIComponent(id)}/solution`);
          leftBody.innerHTML = `<pre class="codeview">${esc(code)}</pre>`;
        } catch (e) {
          leftBody.innerHTML = `<p class="note">${esc(e.message)}</p>`;
        }
      },
    };
    const tabBar = document.getElementById('leftTabs');
    const openTab = (name) => {
      tabBar.querySelectorAll('button').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
      tabs[name]();
    };
    tabBar.onclick = (e) => { if (e.target.dataset.tab) openTab(e.target.dataset.tab); };
    openTab('statement');

    // 실행 / 제출
    const runBtn = document.getElementById('runBtn');
    const submitBtn = document.getElementById('submitBtn');
    const result = document.getElementById('result');
    const customToggle = document.getElementById('customToggle');
    const customBox = document.getElementById('customBox');
    const customInput = document.getElementById('customInput');
    customInput.value = p.sample;
    customToggle.onchange = () => {
      customBox.classList.toggle('hidden', !customToggle.checked);
      runBtn.firstChild.textContent = customToggle.checked ? '입력으로 실행 ' : '샘플 실행 ';
    };

    let busy = false;
    async function judge(kind) {
      if (busy) return;
      busy = true;
      runBtn.disabled = submitBtn.disabled = true;
      result.innerHTML = `<div class="result-empty"><span class="spinner"></span>${kind === 'submit' ? '숨은 테스트 케이스로 채점 중…' : '실행 중…'}</div>`;
      try {
        const body = { code: editor.get() };
        if (kind === 'run' && customToggle.checked) body.input = customInput.value;
        const r = await api(`/api/problems/${encodeURIComponent(id)}/${kind}`, { method: 'POST', body });
        renderResult(result, r);
        if (kind === 'submit' && r.verdict === 'AC') {
          document.getElementById('pMeta').querySelector('.status') ||
            document.getElementById('pMeta').insertAdjacentHTML('beforeend', '<span class="status AC">해결</span>');
        }
      } catch (e) {
        result.innerHTML = `<div class="verdict"><span class="big v-RE">오류</span><span class="sub">${esc(e.message)}</span></div>`;
      } finally {
        busy = false;
        runBtn.disabled = submitBtn.disabled = false;
      }
    }
    runBtn.onclick = () => judge('run');
    submitBtn.onclick = () => judge('submit');
    document.getElementById('resetBtn').onclick = () => {
      if (confirm('작성한 코드를 지우고 처음 템플릿으로 되돌릴까요?')) {
        editor.set(p.template);
        store.set(codeKey, p.template);
      }
    };

    const onKey = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key === 'Enter') { e.preventDefault(); judge('submit'); }
      if (e.key === "'") { e.preventDefault(); judge('run'); }
    };
    document.addEventListener('keydown', onKey);
    view = { leave: () => document.removeEventListener('keydown', onKey), loadCode: (code) => editor.set(code) };
    editor.focus();
  }

  function renderResult(el, r) {
    const label = r.mode === 'sample' ? '샘플' : r.mode === 'custom' ? '직접 입력' : '제출';
    let html = `<div class="verdict">
      <span class="big v-${r.verdict}">${VERDICT[r.verdict]}</span>
      ${r.total ? `<span class="sub">${label} · ${r.passed}/${r.total} 케이스 통과 · ${r.score}점</span>` : `<span class="sub">${label}</span>`}
      <span class="sub">${r.timeMs} ms</span>
    </div>`;
    if (r.cases) {
      html += `<div class="cases">${r.cases.map((c) => {
        const cls = c.score === null ? 'none' : c.score === c.mark ? 'ok' : 'fail';
        return `<span class="case ${cls}">#${c.tc} ${c.score === null ? '-' : c.score}</span>`;
      }).join('')}</div>`;
    }
    if (r.verdict === 'TLE') html += '<div class="out-label">시간 제한 안에 모든 테스트 케이스를 끝내지 못했습니다. "-"로 표시된 케이스는 실행되지 못했습니다.</div>';
    if (r.stdout) html += `<div class="out-label">${r.mode === 'custom' ? '출력' : 'print 출력 (채점에는 영향 없음)'}</div><pre class="out">${esc(r.stdout)}</pre>`;
    if (r.stderr) html += `<div class="out-label">에러</div><pre class="out err">${esc(r.stderr)}</pre>`;
    el.innerHTML = html;
  }

  // ------------------------------------------------------------ 학습
  const isDone = (id) => store.get(`lessonDone:${id}`) === '1';

  // 추천 문제 목록 (외부 사이트 링크는 새 탭으로 연다)
  function practiceHtml(p) {
    if (!p || !p.items.length) return '';
    return `
      <p class="practice-intro">${esc(p.intro)}</p>
      ${p.note ? `<p class="practice-intro"><b>참고:</b> ${esc(p.note)}</p>` : ''}
      <ul class="practice-list">
        ${p.items.map((it) => `
          <li>
            <a href="${esc(it.url)}" target="_blank" rel="noopener noreferrer">${esc(it.title)} ↗</a>
            <span class="site">${esc(it.site)}${it.level ? ` · ${esc(it.level)}` : ''}</span>
            <div class="pnote">${esc(it.note)}</div>
          </li>`).join('')}
      </ul>`;
  }

  async function showLessons() {
    mount('tpl-learn');
    const list = await api('/api/lessons');
    const done = list.filter((l) => isDone(l.id)).length;
    document.getElementById('learnProgress').innerHTML = `
      <div class="bar"><div class="fill" style="width:${Math.round((done / list.length) * 100)}%"></div></div>
      <span>${done} / ${list.length} 완료</span>`;
    const levels = [...new Set(list.map((l) => l.level))];
    document.getElementById('lessonGroups').innerHTML = levels.map((level) => `
      <h2 class="level">${esc(level)}</h2>
      <div class="lesson-list">
        ${list.filter((l) => l.level === level).map((l) => `
          <a class="lesson-card ${isDone(l.id) ? 'done' : ''}" href="#/learn/${esc(l.id)}">
            <span class="check" aria-label="${isDone(l.id) ? '완료' : '미완료'}">${isDone(l.id) ? '✓' : ''}</span>
            <span class="lc-main">
              <strong>${esc(l.title)}</strong>
              <span class="lc-sum">${esc(l.summary)}</span>
            </span>
            <span class="lc-min">${l.minutes}분</span>
          </a>`).join('')}
      </div>`).join('');

    // 외부 사이트 추천 문제 모음
    const pr = await api('/api/lessons/practice');
    document.getElementById('practiceGroups').innerHTML = pr.groups.map((g) => `
      <details class="practice-group">
        <summary>${esc(g.title)} <span class="count">${g.items.length}문제</span></summary>
        ${practiceHtml({ intro: '', items: g.items, note: g.note })}
      </details>`).join('');
    document.getElementById('practiceIntro').textContent = pr.intro;
  }

  async function showLesson(id) {
    mount('tpl-lesson');
    let lesson;
    let list;
    try {
      [lesson, list] = await Promise.all([api(`/api/lessons/${encodeURIComponent(id)}`), api('/api/lessons')]);
    } catch (e) {
      app.innerHTML = `<section class="home"><p>${esc(e.message)}</p><a href="#/learn">학습 목록으로</a></section>`;
      return;
    }
    app.scrollTop = 0;
    document.getElementById('lessonMeta').innerHTML = `<span class="chip">${esc(lesson.level)}</span><span>읽는 시간 약 ${lesson.minutes}분</span>`;
    document.getElementById('lessonTitle').textContent = lesson.title;
    const body = document.getElementById('lessonBody');
    body.innerHTML = lesson.html;

    // 코드 블록에 복사 버튼
    body.querySelectorAll('pre.codeview').forEach((pre) => {
      const wrap = document.createElement('div');
      wrap.className = 'code-wrap';
      pre.replaceWith(wrap);
      wrap.appendChild(pre);
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = '복사';
      btn.onclick = async () => {
        try {
          await navigator.clipboard.writeText(pre.textContent);
          btn.textContent = '복사됨';
        } catch {
          btn.textContent = '복사 실패';
        }
        setTimeout(() => { btn.textContent = '복사'; }, 1500);
      };
      wrap.appendChild(btn);
    });

    if (lesson.practice && lesson.practice.items.length) {
      const sec = document.createElement('section');
      sec.className = 'practice';
      sec.innerHTML = `<h2>더 연습하기 (외부 사이트)</h2>${practiceHtml(lesson.practice)}`;
      body.appendChild(sec);
    }

    const idx = list.findIndex((l) => l.id === id);
    const prev = list[idx - 1];
    const next = list[idx + 1];
    const foot = document.getElementById('lessonFoot');
    foot.innerHTML = `
      ${lesson.problem ? `<a class="btn primary" href="#/p/${esc(lesson.problem)}">연습 문제 풀기: ${esc(lesson.problemTitle || lesson.problem)} →</a>` : ''}
      <button class="btn" id="doneBtn"></button>
      <div class="pager">
        ${prev ? `<a href="#/learn/${esc(prev.id)}">← ${esc(prev.title)}</a>` : '<span></span>'}
        ${next ? `<a href="#/learn/${esc(next.id)}">${esc(next.title)} →</a>` : '<span></span>'}
      </div>`;
    const doneBtn = document.getElementById('doneBtn');
    const paintDone = () => { doneBtn.textContent = isDone(id) ? '✓ 학습 완료 (취소)' : '학습 완료로 표시'; };
    paintDone();
    doneBtn.onclick = () => { store.set(`lessonDone:${id}`, isDone(id) ? '0' : '1'); paintDone(); };
  }

  // ------------------------------------------------------------ 제출 기록
  async function showSubmissions() {
    mount('tpl-submissions');
    const subs = await api('/api/submissions');
    const body = document.getElementById('subBody');
    body.innerHTML = subs.length
      ? subs.map((s) => `<tr>
          <td>${s.id}</td><td><a href="#/p/${esc(s.problemId)}">${esc(s.title)}</a></td>
          <td class="v v-${s.verdict}">${VERDICT[s.verdict]}</td><td>${s.score}</td><td>${s.timeMs}ms</td><td>${fmtTime(s.at)}</td>
          <td><button class="btn ghost small" data-sub="${s.id}">코드</button></td></tr>`).join('')
      : '<tr><td colspan="7" style="color:var(--muted)">아직 제출 기록이 없습니다.</td></tr>';
    body.querySelectorAll('[data-sub]').forEach((b) => {
      b.onclick = () => openCode(subs.find((s) => String(s.id) === b.dataset.sub));
    });
  }

  // ------------------------------------------------------------ 코드 보기 대화상자
  const dialog = document.getElementById('codeDialog');
  let dialogSub = null;
  function openCode(sub) {
    dialogSub = sub;
    document.getElementById('codeDialogTitle').textContent = `#${sub.id} ${sub.title} · ${VERDICT[sub.verdict]} (${sub.score}점)`;
    document.getElementById('codeDialogBody').textContent = sub.code;
    dialog.showModal();
  }
  document.getElementById('codeDialogClose').onclick = () => dialog.close();
  document.getElementById('codeDialogLoad').onclick = () => {
    if (!dialogSub) return;
    store.set(`code:${dialogSub.problemId}`, dialogSub.code);
    dialog.close();
    const target = `#/p/${dialogSub.problemId}`;
    if (location.hash === target && view && view.loadCode) view.loadCode(dialogSub.code);
    else location.hash = target;
  };

  // ------------------------------------------------------------ 시험 모드 타이머
  const exam = document.getElementById('exam');
  const examClock = document.getElementById('examClock');
  const examBtn = document.getElementById('examBtn');
  const pad = (n) => String(n).padStart(2, '0');
  function tick() {
    const start = Number(store.get('examStart')) || 0;
    const left = start ? Math.max(0, start + EXAM_MS - Date.now()) : EXAM_MS;
    const s = Math.floor(left / 1000);
    examClock.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
    exam.classList.toggle('running', !!start);
    exam.classList.toggle('low', !!start && left < 30 * 60 * 1000);
    examBtn.textContent = start ? '시험 종료' : '시험 모드 시작';
    if (start && left === 0 && !store.get('examAlerted')) {
      store.set('examAlerted', '1');
      alert('시험 시간 4시간이 끝났습니다.');
    }
  }
  examBtn.onclick = () => {
    if (store.get('examStart')) {
      if (!confirm('시험 모드를 끝낼까요?')) return;
      store.del('examStart');
    } else {
      store.set('examStart', String(Date.now()));
      store.del('examAlerted');
    }
    tick();
  };
  setInterval(tick, 1000);
  tick();

  route();
})();
