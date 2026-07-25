document.addEventListener('DOMContentLoaded', () => {
  const logoutLink = document.getElementById('logoutLink');
  const tabs = Array.from(document.querySelectorAll('.settings-tab'));
  const panels = {
    account: document.getElementById('accountPanel'),
    privacy: document.getElementById('privacyPanel'),
    security: document.getElementById('securityPanel'),
    theme: document.getElementById('themePanel'),
  };
  const passwordButton = document.getElementById('updatePasswordButton');
  const passwordStatus = document.getElementById('passwordStatus');
  const themeToggle = document.getElementById('darkModeToggle');

  function setTab(tabKey) {
    tabs.forEach((tab) => {
      const isActive = tab.dataset.tab === tabKey;
      tab.style.color = isActive ? 'var(--accent)' : 'var(--text-secondary)';
      tab.style.borderBottom = isActive ? '2px solid var(--accent)' : '2px solid transparent';
    });
    Object.entries(panels).forEach(([key, panel]) => {
      if (panel) {
        panel.style.display = key === tabKey ? 'block' : 'none';
      }
    });
  }

  function applyTheme(theme) {
    const resolvedTheme = theme === 'dark' ? 'dark' : 'light';
    document.body.setAttribute('data-theme', resolvedTheme);
    document.documentElement.setAttribute('data-theme', resolvedTheme);
    if (themeToggle) {
      themeToggle.checked = resolvedTheme === 'dark';
    }
    localStorage.setItem('careflow-theme', resolvedTheme);
  }

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => setTab(tab.dataset.tab));
  });

  if (logoutLink) {
    logoutLink.addEventListener('click', async (event) => {
      event.preventDefault();
      await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
      window.location.href = '/login';
    });
  }

  if (passwordButton) {
    passwordButton.addEventListener('click', async () => {
      const currentPassword = document.getElementById('currentPassword').value.trim();
      const newPassword = document.getElementById('newPassword').value.trim();
      if (!currentPassword || !newPassword) {
        showPasswordStatus('Both current and new password are required.', true);
        return;
      }

      const response = await fetch('/auth/change-password', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const data = await response.json();
      if (!response.ok) {
        showPasswordStatus(data.error || 'Unable to update password.', true);
        return;
      }
      showPasswordStatus('Password updated successfully.', false);
      document.getElementById('currentPassword').value = '';
      document.getElementById('newPassword').value = '';
    });
  }

  if (themeToggle) {
    themeToggle.addEventListener('change', (event) => {
      applyTheme(event.target.checked ? 'dark' : 'light');
    });
  }

  function showPasswordStatus(message, isError) {
    passwordStatus.textContent = message;
    passwordStatus.style.display = 'block';
    passwordStatus.style.color = isError ? '#A93C3C' : 'var(--text-primary)';
    setTimeout(() => { passwordStatus.style.display = 'none'; }, 3000);
  }

  const savedTheme = localStorage.getItem('careflow-theme') || 'light';
  applyTheme(savedTheme);
  setTab('account');
});
