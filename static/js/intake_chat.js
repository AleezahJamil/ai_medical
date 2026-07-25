const state = {
  patientId: document.body.dataset.patientId,
  firstName: document.body.dataset.firstName,
  messages: [],
  step: 0,
  status: 'loading',
  safetyDismissed: false,
};

const stepDots = document.getElementById('stepDots');
const stepLabel = document.getElementById('stepLabel');
const messageContainer = document.getElementById('messageContainer');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const safetyBanner = document.getElementById('safetyBanner');
const dismissSafety = document.getElementById('dismissSafety');
const completeCta = document.getElementById('completeCta');
const logoutLink = document.getElementById('logoutLink');

const setStatus = (status) => {
  state.status = status;
  if (status === 'complete') {
    completeCta.style.display = 'block';
    userInput.disabled = true;
    sendButton.disabled = true;
  }
};

const updateDots = () => {
  const total = 6;
  stepDots.innerHTML = '';
  for (let i = 0; i < total; i += 1) {
    const dot = document.createElement('div');
    dot.style.height = '4px';
    dot.style.flex = '1';
    dot.style.borderRadius = '2px';
    dot.style.background = i <= state.step ? 'var(--accent)' : 'var(--border)';
    stepDots.appendChild(dot);
  }
  const labels = ['Symptoms', 'History', 'Severity', 'Lifestyle', 'Review', 'Complete'];
  stepLabel.textContent = `Step ${Math.min(state.step + 1, total)} of ${total} · ${labels[Math.min(state.step, total - 1)]}`;
};

const renderMessages = () => {
  messageContainer.innerHTML = '';
  state.messages.forEach((msg) => {
    const wrapper = document.createElement('div');
    wrapper.style.display = 'flex';
    wrapper.style.justifyContent = msg.from === 'patient' ? 'flex-end' : 'flex-start';
    const bubble = document.createElement('div');
    bubble.style.maxWidth = '75%';
    bubble.style.padding = '12px 16px';
    bubble.style.borderRadius = '14px';
    bubble.style.fontSize = '14px';
    bubble.style.lineHeight = '1.5';
    bubble.style.background = msg.from === 'patient' ? 'var(--accent)' : 'var(--page-bg)';
    bubble.style.color = msg.from === 'patient' ? '#fff' : 'var(--text-primary)';
    bubble.textContent = msg.text;
    wrapper.appendChild(bubble);
    messageContainer.appendChild(wrapper);
  });
};

const addMessage = (from, text) => {
  state.messages = [...state.messages, { from, text }];
  renderMessages();
};

const startIntake = async () => {
  const response = await fetch('/intake/start', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: state.patientId }),
  });
  if (!response.ok) {
    const error = await response.json();
    addMessage('ai', error.error || 'Unable to start intake.');
    return;
  }
  addMessage('ai', `Hi ${state.firstName}, I'm the CareFlow intake assistant. What's the main thing you'd like to talk about today?`);
  setStatus('in_progress');
  updateDots();
};

const sendMessage = async () => {
  const text = userInput.value.trim();
  if (!text || state.status === 'complete') return;
  addMessage('patient', text);
  userInput.value = '';
  setStatus('waiting');

  const response = await fetch('/intake/message', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: state.patientId, message: text }),
  });

  if (!response.ok) {
    const error = await response.json();
    addMessage('ai', error.error || 'Unable to send message.');
    setStatus('in_progress');
    return;
  }

  const result = await response.json();
  if (result.status === 'emergency') {
    addMessage('ai', result.message);
    safetyBanner.style.display = 'flex';
    setStatus('complete');
    return;
  }

  addMessage('ai', result.message);
  if (result.status === 'complete') {
    setStatus('complete');
  } else {
    setStatus('in_progress');
    state.step = Math.min(state.step + 1, 5);
  }
  updateDots();
};

const initialize = async () => {
  if (!state.patientId) {
    window.location.href = '/login';
    return;
  }

  logoutLink.addEventListener('click', async (event) => {
    event.preventDefault();
    await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.href = '/login';
  });

  dismissSafety.addEventListener('click', () => {
    state.safetyDismissed = true;
    safetyBanner.style.display = 'none';
  });

  sendButton.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      sendMessage();
    }
  });

  updateDots();
  startIntake();
};

initialize();
