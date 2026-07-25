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
const resendField = document.getElementById('resendField');
const resendEmailInput = document.getElementById('resendEmailInput');
const resendButton = document.getElementById('resendButton');

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

const setMessage = (text, isError = true) => {
  messageContainer.textContent = text;
  messageContainer.style.color = isError ? '#E0524A' : '#2E7D5B';
};

const clearError = () => {
  messageContainer.textContent = '';
};

const showResend = (prefillEmail) => {
  resendField.style.display = 'block';
  if (prefillEmail) {
    resendEmailInput.value = prefillEmail;
  }
};

const hideResend = () => {
  resendField.style.display = 'none';
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
  clearError();
  hideResend();
  updateUi();
});

authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearError();
  hideResend();

  const email = emailInput.value.trim();
  const password = passwordInput.value.trim();

  if (!email || !password) {
    setMessage('Email and password are required.');
    return;
  }

  const payload = { email, password };
  let url = '/auth/login';
  const isSignup = state.mode === 'register';

  if (isSignup) {
    const name = (nameInput?.value || '').trim();
    if (!name) {
      setMessage('Full name is required to create an account.');
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
      setMessage(result.error || 'An error occurred.');
      if (result.error_code === 'unverified') {
        showResend(email);
      }
      return;
    }

    if (isSignup) {
      // Signup no longer logs the user in — they must verify their email first.
      setMessage(`Account created. Please check ${result.email || email} to verify your account before logging in.`, false);
      state.mode = 'login';
      updateUi();
      return;
    }

    const role = result.role || state.role;
    if (role === 'patient') {
      window.location.href = '/patient/dashboard';
      return;
    }
    if (role === 'admin') {
      window.location.href = '/admin/dashboard';
      return;
    }

    window.location.href = '/doctor/dashboard';
  } catch (error) {
    setMessage('Network error. Please try again.');
  }
});

resendButton.addEventListener('click', async () => {
  const email = (resendEmailInput.value || '').trim();
  if (!email) {
    setMessage('Enter your email to resend the verification link.');
    return;
  }

  resendButton.disabled = true;
  const originalLabel = resendButton.textContent;
  resendButton.textContent = 'Sending…';

  try {
    const response = await fetch('/auth/resend-verification', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const result = await response.json();
    setMessage(result.status || 'If that email exists, a new verification link has been sent.', false);
  } catch (error) {
    setMessage('Network error. Please try again.');
  } finally {
    resendButton.disabled = false;
    resendButton.textContent = originalLabel;
  }
});

const applyVerificationQueryParams = () => {
  const params = new URLSearchParams(window.location.search);
  const verified = params.get('verified');
  const verifyError = params.get('verify_error');

  if (verified === '1') {
    setMessage('Email verified. You can now log in.', false);
  } else if (verifyError === 'expired') {
    setMessage('That verification link has expired. Enter your email below to get a new one.');
    showResend();
  } else if (verifyError === 'invalid') {
    setMessage('That verification link is invalid. Enter your email below to get a new one.');
    showResend();
  }
};

applyVerificationQueryParams();
updateUi();
