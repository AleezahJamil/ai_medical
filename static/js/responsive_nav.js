(function () {
  function init() {
    var sidebar = document.querySelector('.cf-sidebar');
    var toggle = document.querySelector('.cf-hamburger');
    var backdrop = document.querySelector('.cf-sidebar-backdrop');
    if (!sidebar || !toggle || !backdrop) return;

    function open() {
      sidebar.classList.add('cf-open');
      backdrop.classList.add('cf-open');
    }

    function close() {
      sidebar.classList.remove('cf-open');
      backdrop.classList.remove('cf-open');
    }

    toggle.addEventListener('click', function () {
      if (sidebar.classList.contains('cf-open')) {
        close();
      } else {
        open();
      }
    });

    backdrop.addEventListener('click', close);

    sidebar.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', close);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
