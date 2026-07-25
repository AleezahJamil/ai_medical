const patientId = document.body.dataset.patientId;
const doctorNames = JSON.parse(document.body.dataset.doctorNames || '{}');
const upcomingList = document.getElementById('upcomingList');
const pastList = document.getElementById('pastList');
const statusMessage = document.getElementById('statusMessage');
const bookButton = document.getElementById('bookButton');
const bookingModal = document.getElementById('bookingModal');
const doctorSelect = document.getElementById('doctorSelect');
const slotsContainer = document.getElementById('slotsContainer');
const noSlots = document.getElementById('noSlots');
const closeBooking = document.getElementById('closeBooking');
const confirmBooking = document.getElementById('confirmBooking');
const cancelBooking = document.getElementById('cancelBooking');

let selectedSlot = null;
let selectedDoctor = null;

function formatSlot(slot) {
  let dt = new Date(slot);
  if (isNaN(dt.getTime())) {
    const normalized = slot.replace(' ', 'T');
    dt = new Date(normalized);
  }
  if (isNaN(dt.getTime())) {
    return { date: slot.split(' ')[0] || slot, time: slot.split(' ')[1] || '' };
  }
  const date = dt.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  const time = dt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return { date, time };
}

function getDoctorName(doctorId) {
  return doctorNames[doctorId] || 'Unknown doctor';
}

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.style.display = 'block';
  statusMessage.style.background = isError ? '#FDECEA' : '#F5F5FF';
  statusMessage.style.color = isError ? '#A93C3C' : '#3B3B6D';
}

function clearStatus() {
  statusMessage.style.display = 'none';
}

function buildAppointmentCard(appointment, isUpcoming) {
  const card = document.createElement('div');
  card.style.background = '#FFFFFF';
  card.style.border = '1px solid #E7E5F1';
  card.style.borderRadius = '12px';
  card.style.padding = '18px 20px';
  card.style.display = 'flex';
  card.style.alignItems = 'center';
  card.style.justifyContent = 'space-between';
  card.style.marginBottom = '12px';
  if (!isUpcoming) {
    card.style.opacity = '0.75';
  }

  const left = document.createElement('div');
  const title = document.createElement('div');
  title.style.fontSize = '15px';
  title.style.fontWeight = '700';
  title.style.color = '#1E1B2E';
  title.textContent = getDoctorName(appointment.doctor_id);

  const subtitle = document.createElement('div');
  subtitle.style.fontSize = '13px';
  subtitle.style.color = '#6B6880';
  const statusText = appointment.status ? ` • ${appointment.status}` : '';
  subtitle.textContent = `${appointment.specialty || 'Primary care'} • ${appointment.location || 'Office visit'}${statusText}`;

  left.appendChild(title);
  left.appendChild(subtitle);

  const { date, time } = formatSlot(appointment.slot);
  const right = document.createElement('div');
  right.style.display = 'flex';
  right.style.alignItems = 'center';
  right.style.gap = '16px';

  const dateBlock = document.createElement('div');
  dateBlock.style.textAlign = 'right';
  const dateEl = document.createElement('div');
  dateEl.style.fontSize = '14px';
  dateEl.style.fontWeight = '700';
  dateEl.style.color = '#1E1B2E';
  dateEl.textContent = date;
  const timeEl = document.createElement('div');
  timeEl.style.fontSize = '13px';
  timeEl.style.color = '#6B6880';
  timeEl.textContent = time;
  dateBlock.appendChild(dateEl);
  dateBlock.appendChild(timeEl);

  right.appendChild(dateBlock);

  if (isUpcoming && appointment.status === 'scheduled') {
    const button = document.createElement('button');
    button.style.background = '#FDECEA';
    button.style.color = '#E0524A';
    button.style.border = 'none';
    button.style.fontFamily = "'Inter',sans-serif";
    button.style.fontSize = '13px';
    button.style.fontWeight = '700';
    button.style.padding = '8px 14px';
    button.style.borderRadius = '8px';
    button.style.cursor = 'pointer';
    button.textContent = 'Cancel';
    button.addEventListener('click', () => cancelAppointment(appointment.appointment_id));
    right.appendChild(button);
  }

  card.appendChild(left);
  card.appendChild(right);
  return card;
}

async function fetchAppointments() {
  clearStatus();
  try {
    const response = await fetch(`/patient/${encodeURIComponent(patientId)}/appointments`);
    if (!response.ok) {
      throw new Error('Unable to load appointments.');
    }
    const data = await response.json();
    renderAppointments(data);
  } catch (err) {
    showStatus(err.message, true);
  }
}

// ---------------- BOOKING FLOW ----------------
function openBooking() {
  // populate doctors
  doctorSelect.innerHTML = '';
  Object.entries(doctorNames || {}).forEach(([id, name]) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = name;
    doctorSelect.appendChild(opt);
  });
  if (!doctorSelect.options.length) {
    const opt = document.createElement('option'); opt.value = ''; opt.textContent = 'No doctors available'; doctorSelect.appendChild(opt);
  }
  selectedDoctor = doctorSelect.value || doctorSelect.options[0]?.value;
  selectedSlot = null;
  slotsContainer.innerHTML = '';
  noSlots.style.display = 'none';
  bookingModal.style.display = 'flex';
  if (selectedDoctor) fetchSlotsForDoctor(selectedDoctor);
}

function closeBookingModal() {
  bookingModal.style.display = 'none';
}

async function fetchSlotsForDoctor(doctorId) {
  slotsContainer.innerHTML = '';
  noSlots.style.display = 'none';
  try {
    const resp = await fetch(`/doctor/${encodeURIComponent(doctorId)}/slots`);
    if (!resp.ok) throw new Error('Failed to load slots');
    const data = await resp.json();
    const slots = data && data.available_slots ? data.available_slots : [];
    if (!slots.length) {
      noSlots.style.display = 'block';
      return;
    }
    slots.forEach((s) => {
      const btn = document.createElement('button');
      btn.textContent = (new Date(s.replace(' ', 'T'))).toLocaleString();
      btn.style.padding = '8px 12px';
      btn.style.border = '1px solid #E7E5F1';
      btn.style.borderRadius = '8px';
      btn.style.background = '#FFFFFF';
      btn.style.cursor = 'pointer';
      btn.addEventListener('click', () => {
        selectedSlot = s;
        Array.from(slotsContainer.children).forEach(c => c.style.boxShadow = 'none');
        btn.style.boxShadow = '0 4px 12px rgba(90,72,189,0.12)';
      });
      slotsContainer.appendChild(btn);
    });
  } catch (err) {
    noSlots.style.display = 'block';
    noSlots.textContent = 'Unable to load slots.';
  }
}

function normalizeSlot(slot) {
  if (!slot || typeof slot !== 'string') return '';
  const normalized = slot.replace('T', ' ').trim();
  const parts = normalized.split(' ');
  if (parts.length < 2) return normalized;
  const date = parts[0];
  let timePart = parts[1];
  if (timePart.includes(':')) {
    const timeParts = timePart.split(':');
    if (timeParts.length >= 2) {
      timePart = `${timeParts[0].padStart(2, '0')}:${timeParts[1].padStart(2, '0')}`;
    }
  }
  return `${date} ${timePart}`;
}

async function doConfirmBooking() {
  if (!selectedDoctor || !selectedDoctor.trim()) {
    showStatus('Please select a doctor.', true);
    return;
  }
  if (!selectedSlot || !selectedSlot.trim()) {
    showStatus('Please select a slot.', true);
    return;
  }

  const formattedSlot = normalizeSlot(selectedSlot);
  const requestBody = {
    patient_id: patientId,
    doctor_id: selectedDoctor,
    slot: formattedSlot,
  };

  try {
    const resp = await fetch(`/patient/book`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || 'Booking failed');
    }
    showStatus('Booking confirmed.');
    closeBookingModal();
    await fetchAppointments();
  } catch (err) {
    showStatus(err.message, true);
  }
}

// event wiring
bookButton.addEventListener('click', openBooking);
closeBooking.addEventListener('click', closeBookingModal);
cancelBooking.addEventListener('click', closeBookingModal);
doctorSelect.addEventListener('change', (e) => {
  selectedDoctor = e.target.value;
  selectedSlot = null;
  Array.from(slotsContainer.children).forEach((c) => { c.style.boxShadow = 'none'; });
  fetchSlotsForDoctor(selectedDoctor);
});
confirmBooking.addEventListener('click', doConfirmBooking);

function sortAppointments(appointments) {
  return appointments.slice().sort((a, b) => new Date(a.slot) - new Date(b.slot));
}

function renderAppointments(appointments) {
  upcomingList.innerHTML = '';
  pastList.innerHTML = '';
  if (!Array.isArray(appointments) || appointments.length === 0) {
    upcomingList.innerHTML = `<div style="padding:24px 18px;border-radius:16px;background:#FFFFFF;border:1px solid #E7E5F1;color:#6B6880;font-size:14px">No appointments found.</div>`;
    pastList.innerHTML = `<div style="padding:24px 18px;border-radius:16px;background:#FFFFFF;border:1px solid #E7E5F1;color:#6B6880;font-size:14px">No past visits yet.</div>`;
    return;
  }

  const sorted = sortAppointments(appointments);
  const now = new Date();
  const upcoming = sorted.filter((apt) => new Date(apt.slot) >= now && apt.status !== 'cancelled');
  const past = sorted.filter((apt) => new Date(apt.slot) < now || apt.status === 'completed' || apt.status === 'cancelled');

  if (upcoming.length === 0) {
    upcomingList.innerHTML = `<div style="padding:24px 18px;border-radius:16px;background:#FFFFFF;border:1px solid #E7E5F1;color:#6B6880;font-size:14px">No upcoming appointments.</div>`;
  } else {
    upcoming.forEach((apt) => upcomingList.appendChild(buildAppointmentCard(apt, true)));
  }

  if (past.length === 0) {
    pastList.innerHTML = `<div style="padding:24px 18px;border-radius:16px;background:#FFFFFF;border:1px solid #E7E5F1;color:#6B6880;font-size:14px">No past appointments.</div>`;
  } else {
    past.forEach((apt) => pastList.appendChild(buildAppointmentCard(apt, false)));
  }
}

async function cancelAppointment(appointmentId) {
  try {
    const response = await fetch(`/appointment/${encodeURIComponent(appointmentId)}/cancel`, {
      method: 'POST',
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || 'Unable to cancel appointment.');
    }
    showStatus('Appointment cancelled.');
    await fetchAppointments();
  } catch (err) {
    showStatus(err.message, true);
  }
}

window.addEventListener('DOMContentLoaded', fetchAppointments);
