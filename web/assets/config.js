(function () {
  // 우선순위: window.API_BASE(페이지 상수) > localStorage > 로컬 기본(개발)
  const saved = localStorage.getItem('API_BASE');
  const fallback = 'http://127.0.0.1:8088';
  window.API_BASE = window.API_BASE || saved || fallback;

  window.setApiBase = function (url) {
    try {
      if (!/^https?:\/\//.test(url)) throw new Error('http/https로 시작해야 합니다');
      localStorage.setItem('API_BASE', url);
      window.API_BASE = url;
      alert('API 연결이 설정되었습니다: ' + url + '\n화면을 새로고침합니다.');
      location.reload();
    } catch (e) {
      alert('설정 실패: ' + e.message);
    }
  };
})();
