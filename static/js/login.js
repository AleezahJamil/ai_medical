const state = {
  mode: 'login',
  role: 'patient',
};

const loginTab = document.getElementById('loginTab');
const registerTab = document.getElementById('registerTab');
const patientTab = document.getElementById('patientTab');
const doctorTab = document.getElementById('doctorTab');
const submitButton = document.getElementById('submitButton');
const switchPrompt = document.getElementById('switchPrompt');
const switchLink = document.getElementById('switchLink');
const messageContainer = document.getElementById('messageContainer');
const emailInput = document.getElementById('emailInput');
const passwordInput = document.getElementById('passwordInput');
const nameInput = document.getElementById('nameInput');
const nameField = document.getElementById('nameField');
const authForm = document.getElementById('authForm');

const updateUi = () => {
  const isLogin = state.mode === 'login';
  loginTab.style.background = isLogin ? '#FFFFFF' : 'transparent';
  loginTab.style.color = isLogin ? '#1E1B2E' : '#6B6880';
  registerTab.style.background = isLogin ? 'transparent' : '#FFFFFF';
  registerTab.style.color = isLogin ? '#6B6880' : '#1E1B2E';

  patientTab.style.border = state.role === 'patient' ? '1px solid #6D5BD0' : '1px solid #E7E5F1';
  patientTab.style.background = state.role === 'patient' ? '#EFECFB' : '#FFFFFF';
  patientTab.style.color = state.role === 'patient' ? '#5A48BD' : '#6B6880';
  doctorTab.style.border = state.role === 'doctor' ? '1px solid #6D5BD0' : '1px solid #E7E5F1';
  doctorTab.style.background = state.role === 'doctor' ? '#EFECFB' : '#FFFFFF';
  doctorTab.style.color = state.role === 'doctor' ? '#5A48BD' : '#6B6880';

  submitButton.textContent = isLogin ? 'Log in' : 'Create account';
  switchPrompt.textContent = isLogin ? "Don't have an account?" : 'Already have an account?';
  switchLink.textContent = isLogin ? 'Create one' : 'Log in';
  nameField.style.display = isLogin ? 'none' : 'block';
};

const setError = (text) => {
  messageContainer.textContent = text;
};

const clearError = () => {
  messageContainer.textContent = '';
};

loginTab.addEventListener('click', () => {
  state.mode = 'login';
  updateUi();
});
registerTab.addEventListener('click', () => {
  state.mode = 'register';
  updateUi();
});
patientTab.addEventListener('click', () => {
  state.role = 'patient';
  updateUi();
});
doctorTab.addEventListener('click', () => {
  state.role = 'doctor';
  updateUi();
});
switchLink.addEventListener('click', (event) => {
  event.preventDefault();
  state.mode = state.mode === 'login' ? 'register' : 'login';
  updateUi();
});

authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearError();

  const email = emailInput.value.trim();
  const password = passwordInput.value.trim();

  if (!email || !password) {
    setError('Email and password are required.');
    return;
  }

  const payload = { email, password };
  let url = '/auth/login';

  if (state.mode === 'register') {
    const name = (nameInput?.value || '').trim();
    if (!name) {
      setError('Full name is required to create an account.');
      return;
    }
    payload.name = name;
    payload.role = state.role;
    url = '/auth/signup';
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      setError(result.error || 'An error occurred.');
      return;
    }

    const role = result.role || state.role;
    if (role === 'patient') {
      window.location.href = '/patient/dashboard';
      return;
    }

    window.location.href = '/doctor/dashboard';
  } catch (error) {
    setError('Network error. Please try again.');
  }
});

updateUi();
