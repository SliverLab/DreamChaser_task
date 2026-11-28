/*
 * 本地练习站前端逻辑。
 * 全部在浏览器本地完成:不发任何网络请求,不连任何外部服务,不碰任何真实数据。
 */
(function () {
  'use strict';

  var KEY = 'pw_user';
  // 练习账号,不是真实凭据
  var USER = 'student';
  var PASS = 'week4pass';

  function cookieValue() {
    var m = document.cookie.match(new RegExp('(?:^|;\\s*)' + KEY + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  function whoami() {
    return cookieValue() || localStorage.getItem(KEY) || '';
  }

  function requireAuth(redirect) {
    if (!whoami()) {
      location.replace(redirect);
      return false;
    }
    var slot = document.querySelector('[data-user]');
    if (slot) slot.textContent = whoami();
    return true;
  }

  function login(user, pass) {
    if (user !== USER || pass !== PASS) {
      return '用户名或密码不正确';
    }
    // 同时写 cookie 与 localStorage,方便演示会话状态保存与恢复
    document.cookie = KEY + '=' + encodeURIComponent(user) + '; path=/; max-age=86400; SameSite=Lax';
    localStorage.setItem(KEY, user);
    return '';
  }

  function logout() {
    document.cookie = KEY + '=; path=/; max-age=0';
    localStorage.removeItem(KEY);
    location.href = 'index.html';
  }

  function initLogin() {
    var form = document.getElementById('login-form');
    if (!form) return;
    var tip = document.getElementById('tip');
    if (whoami()) {
      tip.className = 'notice';
      tip.textContent = '当前已登录为 ' + whoami() + ',可以直接进入文章列表。';
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = login(
        document.getElementById('username').value.trim(),
        document.getElementById('password').value
      );
      if (msg) {
        tip.className = 'error';
        tip.textContent = msg;
        return;
      }
      location.href = 'list.html';
    });
  }

  function initList() {
    var box = document.getElementById('results');
    if (!box) return;

    var input = document.getElementById('q');
    var count = document.getElementById('count');
    var tagBar = document.getElementById('tags');
    var activeTag = '';

    var allTags = [];
    window.ARTICLES.forEach(function (a) {
      a.tags.forEach(function (t) {
        if (allTags.indexOf(t) === -1) allTags.push(t);
      });
    });

    var allBtn = document.createElement('button');
    allBtn.type = 'button';
    allBtn.textContent = '全部';
    allBtn.className = 'active';
    allBtn.addEventListener('click', function () { setTag(''); });
    tagBar.appendChild(allBtn);

    allTags.forEach(function (t) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = t;
      b.addEventListener('click', function () { setTag(t); });
      tagBar.appendChild(b);
    });

    function setTag(t) {
      activeTag = t;
      Array.prototype.forEach.call(tagBar.children, function (b, i) {
        var isAll = i === 0;
        var on = isAll ? t === '' : b.textContent === t;
        b.classList.toggle('active', on);
      });
      render();
    }

    function render() {
      var q = (input.value || '').trim().toLowerCase();
      var items = window.ARTICLES.filter(function (a) {
        var hitTag = !activeTag || a.tags.indexOf(activeTag) !== -1;
        var hay = (a.title + ' ' + a.excerpt + ' ' + (a.body || '') + ' ' + a.tags.join(' ')).toLowerCase();
        return hitTag && (!q || hay.indexOf(q) !== -1);
      });

      count.textContent = '共 ' + items.length + ' 篇' +
        (activeTag ? '(标签:' + activeTag + ')' : '') +
        (q ? '(关键词:' + q + ')' : '');

      if (!items.length) {
        box.innerHTML = '<p class="empty">没有匹配的文章。换个关键词或取消标签筛选再试。</p>';
        return;
      }

      box.innerHTML = items.map(function (a) {
        return '<div class="card">' +
          '<h3><a href="' + a.url + '">' + a.title + '</a></h3>' +
          '<p>' + a.excerpt + '</p>' +
          a.tags.map(function (t) { return '<span class="tag">' + t + '</span>'; }).join('') +
          '</div>';
      }).join('');
    }

    input.addEventListener('input', render);
    render();
  }

  function initPractice() {
    // 两步确认:刻意不用原生 confirm()。Playwright 默认会自动 dismiss 原生弹框,
    // 那样点击后页面毫无变化,演示"删除需确认"会看起来像按钮坏了。
    var del = document.getElementById('delete-btn');
    var delConfirm = document.getElementById('delete-confirm-btn');
    var delResult = document.getElementById('delete-result');

    if (del) {
      del.addEventListener('click', function () {
        if (delConfirm) delConfirm.style.display = 'inline-block';
        if (delResult) delResult.textContent = '已请求删除。还需要再点一次「确认删除」才会执行。';
      });
    }

    if (delConfirm) {
      delConfirm.addEventListener('click', function () {
        delConfirm.style.display = 'none';
        if (delResult) {
          delResult.textContent =
            '已删除《练习用示例文章》。这只是一次本地演示,没有删除任何文件或数据。';
        }
      });
    }

    var send = document.getElementById('comment-btn');
    if (send) {
      send.addEventListener('click', function () {
        var text = document.getElementById('comment-text').value.trim();
        var out = document.getElementById('comment-result');
        if (!text) {
          out.textContent = '评论内容不能为空。';
          return;
        }
        out.textContent = '已在本页记录一条练习评论:' + text + '(未发送到任何外部服务)';
      });
    }
  }

  window.PW = {
    requireAuth: requireAuth,
    whoami: whoami,
    login: login,
    logout: logout
  };

  document.addEventListener('DOMContentLoaded', function () {
    initLogin();
    initList();
    initPractice();
  });
})();
