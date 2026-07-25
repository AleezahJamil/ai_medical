const patientId = document.body.dataset.patientId;
const firstName = document.body.dataset.firstName;
const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const documentsList = document.getElementById("documentsList");

function setStatus(message, visible = true) {
  uploadStatus.textContent = message;
  uploadStatus.style.display = visible ? "block" : "none";
}

function renderDocuments(documents) {
  documentsList.innerHTML = "";
  if (!documents || documents.length === 0) {
    documentsList.innerHTML = `<div style=\"padding:24px 18px;border-radius:16px;background:var(--surface);border:1px solid var(--border);color:var(--text-secondary);font-size:14px;\">No documents uploaded yet. Upload a report to see a summary here.</div>`;
    return;
  }

  documents.forEach((doc) => {
    const card = document.createElement("div");
    card.style.background = "var(--surface)";
    card.style.border = "1px solid var(--border)";
    card.style.borderRadius = "20px";
    card.style.padding = "22px";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.gap = "10px";

    const title = document.createElement("div");
    title.style.fontSize = "16px";
    title.style.fontWeight = "800";
    title.style.color = "var(--text-primary)";
    title.textContent = doc.filename || "Uploaded document";

    const summary = document.createElement("div");
    summary.style.fontSize = "14px";
    summary.style.color = "var(--text-secondary)";
    summary.textContent = doc.summary || "No summary available.";

    const meta = document.createElement("div");
    meta.style.display = "flex";
    meta.style.justifyContent = "space-between";
    meta.style.flexWrap = "wrap";
    meta.style.gap = "8px";

    const typeTag = document.createElement("span");
    typeTag.style.fontSize = "12px";
    typeTag.style.fontWeight = "700";
    typeTag.style.color = "var(--accent)";
    typeTag.style.textTransform = "uppercase";
    typeTag.textContent = doc.filename?.split(".").pop()?.toUpperCase() || "FILE";

    const dateTag = document.createElement("span");
    dateTag.style.fontSize = "12px";
    dateTag.style.color = "var(--text-secondary)";
    dateTag.textContent = doc.uploaded_at || doc.uploadedAt || "Upload date unavailable";

    const statusTag = document.createElement("span");
    statusTag.style.fontSize = "12px";
    statusTag.style.fontWeight = "700";
    statusTag.style.color = doc.summary ? "var(--success)" : "var(--text-secondary)";
    statusTag.textContent = doc.summary ? "Analyzed" : "Pending";

    meta.appendChild(typeTag);
    meta.appendChild(dateTag);
    meta.appendChild(statusTag);
    card.appendChild(title);
    card.appendChild(summary);
    card.appendChild(meta);
    documentsList.appendChild(card);
  });
}

async function fetchDocuments() {
  try {
    const response = await fetch(`/patient/documents/data`);
    if (!response.ok) {
      throw new Error("Unable to load documents.");
    }
    const data = await response.json();
    renderDocuments(data);
  } catch (err) {
    documentsList.innerHTML = `<div style=\"padding:24px 18px;border-radius:16px;background:var(--danger-soft);border:1px solid var(--danger);color:var(--danger);font-size:14px;\">${err.message}</div>`;
  }
}

async function uploadFile(file) {
  setStatus("Analyzing document…", true);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`/patient/upload/${patientId}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Upload failed.");
    }

    await fetchDocuments();
    setStatus("Upload complete. Document summary updated.", true);
    setTimeout(() => setStatus("", false), 3200);
  } catch (err) {
    setStatus(err.message, true);
  }
}

uploadArea.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (event) => {
  if (!event.target.files || event.target.files.length === 0) {
    return;
  }
  uploadFile(event.target.files[0]);
});

uploadArea.addEventListener("dragover", (event) => {
  event.preventDefault();
  uploadArea.style.background = "var(--accent-soft)";
});
uploadArea.addEventListener("dragleave", () => {
  uploadArea.style.background = "var(--surface)";
});
uploadArea.addEventListener("drop", (event) => {
  event.preventDefault();
  uploadArea.style.background = "var(--surface)";
  if (event.dataTransfer.files.length > 0) {
    uploadFile(event.dataTransfer.files[0]);
  }
});

window.addEventListener("DOMContentLoaded", () => {
  fetchDocuments();
});
