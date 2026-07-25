const doctorId = document.body.dataset.doctorId;
const availableSlotsContainer = document.getElementById('availableSlots');
const slotInput = document.getElementById('slotInput');
const addSlotButton = document.getElementById('addSlotButton');
const slotStatus = document.getElementById('slotStatus');
const doctorLogout = document.getElementById('doctorLogout');

function showSlotStatus(message, isError = false) {
  slotStatus.textContent = message;
  slotStatus.style.display = 'block';
  slotStatus.style.color = isError ? '#A93C3C' : '#3B3B6D';
}

function clearSlotStatus() {
  slotStatus.textContent = '';
  slotStatus.style.display = 'none';
}

function formatSlotLabel(slot) {
  const dt = new Date(slot.replace(' ', 'T'));
  if (isNaN(dt.getTime())) return slot;
  return dt.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function renderAvailableSlots(slots) {
  availableSlotsContainer.innerHTML = '';
  if (!slots || slots.length === 0) {
    availableSlotsContainer.innerHTML = '<div style="padding:18px;border-radius:12px;background:#F7F7FB;color:#6B6880">No available slots added yet.</div>';
    return;
  }
  slots.forEach((slot) => {
    const slotRow = document.createElement('div');
    slotRow.style.display = 'flex';
    slotRow.style.alignItems = 'center';
    slotRow.style.justifyContent = 'space-between';
    slotRow.style.padding = '14px 16px';
    slotRow.style.border = '1px solid #E7E5F1';
    slotRow.style.borderRadius = '12px';
    slotRow.style.background = '#FFFFFF';
    slotRow.style.fontSize = '14px';
    slotRow.style.color = '#1E1B2E';

    const label = document.createElement('div');
    label.textContent = formatSlotLabel(slot);
    slotRow.appendChild(label);

    availableSlotsContainer.appendChild(slotRow);
  });
}

async function fetchAvailableSlots() {
  clearSlotStatus();
  try {
    const response = await fetch(`/doctor/${encodeURIComponent(doctorId)}/slots`);
    if (!response.ok) {
      throw new Error('Unable to load available slots.');
    }
    const data = await response.json();
    renderAvailableSlots(data.available_slots || []);
  } catch (err) {
    showSlotStatus(err.message, true);
  }
}

async function addAvailableSlot() {
  clearSlotStatus();
  const value = slotInput.value;
  if (!value) {
    showSlotStatus('Select a date and time for the slot.', true);
    return;
  }

  const payload = { slot: value.replace('T', ' ') };
  try {
    const response = await fetch(`/doctor/${encodeURIComponent(doctorId)}/slots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Failed to add slot');
    }
    slotInput.value = '';
    showSlotStatus('Slot added successfully.');
    await fetchAvailableSlots();
  } catch (err) {
    showSlotStatus(err.message, true);
  }
}

doctorLogout.addEventListener('click', async (event) => {
  event.preventDefault();
  try {
    await fetch('/auth/logout', { method: 'POST', credentials: 'same-origin' });
  } catch (err) {
    // ignore logout errors and still redirect to login
  }
  window.location.href = '/login';
});
addSlotButton.addEventListener('click', addAvailableSlot);
window.addEventListener('DOMContentLoaded', fetchAvailableSlots);
