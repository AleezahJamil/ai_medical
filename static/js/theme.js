window.CFTheme = (function () {
  var STORAGE_KEY = 'careflow-theme';

  function current() {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light';
    } catch (e) {
      return 'light';
    }
  }

  function apply(theme) {
    var resolved = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', resolved);
    try {
      localStorage.setItem(STORAGE_KEY, resolved);
    } catch (e) {
      // localStorage unavailable (private mode / disabled) — theme just won't persist
    }
    return resolved;
  }

  function initToggle(toggleEl) {
    if (!toggleEl) return;
    toggleEl.checked = current() === 'dark';
    toggleEl.addEventListener('change', function (event) {
      apply(event.target.checked ? 'dark' : 'light');
    });
  }

  return { current: current, apply: apply, initToggle: initToggle };
})();
