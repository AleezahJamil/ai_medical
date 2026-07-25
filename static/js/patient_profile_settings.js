document.addEventListener('DOMContentLoaded', () => {
  const logoutLink = document.getElementById('logoutLink');
  const profileForm = document.getElementById('profileForm');
  const statusMessage = document.getElementById('statusMessage');

  logoutLink.addEventListener('click', async (event) => {
    event.preventDefault();
    await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.href = '/login';
  });

  profileForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = document.getElementById('nameInput').value.trim();
    const email = document.getElementById('emailInput').value.trim();
    const phone = document.getElementById('phoneInput').value.trim();
    const dob = document.getElementById('dobInput').value.trim();

    if (!name || !email) {
      showStatus('Name and email are required.', true);
      return;
    }

    const response = await fetch('/patient/profile-settings', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, phone, dob }),
    });
    const data = await response.json();
    if (!response.ok) {
      showStatus(data.error || 'Unable to save profile.', true);
      return;
    }
    showStatus('Profile saved successfully.', false);
  });

  function showStatus(message, isError) {
    statusMessage.textContent = message;
    statusMessage.style.display = 'block';
    statusMessage.style.background = isError ? 'var(--danger-soft)' : 'var(--accent-soft)';
    statusMessage.style.color = isError ? 'var(--danger)' : 'var(--accent)';
    if (!isError) {
      setTimeout(() => { statusMessage.style.display = 'none'; }, 3000);
    }
  }
});
