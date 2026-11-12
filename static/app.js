// Front-end logic: send the photo to /api/scan, fill the form, download .vcf from /api/vcard.
const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const preview = document.getElementById("preview");
const dropText = document.getElementById("drop-text");
const scanButton = document.getElementById("scan");
const downloadButton = document.getElementById("download");
const statusLine = document.getElementById("status");
const meta = document.getElementById("meta");
const form = document.getElementById("form");

let selectedFile = null;

function setStatus(text, kind = "") {
  statusLine.textContent = text;
  statusLine.className = kind;
}

function selectFile(file) {
  selectedFile = file;
  preview.src = URL.createObjectURL(file);  // show the photo without uploading it
  preview.hidden = false;
  dropText.hidden = true;
  scanButton.disabled = false;
  setStatus(`${file.name}, ${(file.size / 1024).toFixed(0)} КБ`);
}

// Choosing a file with the dialog
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) selectFile(fileInput.files[0]);
});

// Drag-and-drop
drop.addEventListener("dragover", (event) => { event.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  if (event.dataTransfer.files.length > 0) selectFile(event.dataTransfer.files[0]);
});

// "Try a sample": load the sample card from the server as if the user chose it
document.getElementById("sample").addEventListener("click", async () => {
  const response = await fetch("/samples/card_uk.png");
  const blob = await response.blob();
  selectFile(new File([blob], "card_uk.png", { type: "image/png" }));
});

// Send the photo for recognition
scanButton.addEventListener("click", async () => {
  const data = new FormData();
  data.append("file", selectedFile);
  scanButton.disabled = true;
  setStatus("Розпізнаю… (зазвичай 2–20 с)");
  try {
    const response = await fetch("/api/scan", { method: "POST", body: data });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail);
    fillForm(result.contact);
    meta.textContent = `Модель: ${result.model} · час очікування: ${result.seconds} с`;
    downloadButton.disabled = false;
    setStatus("Готово. Перевірте поля і за потреби виправте.", "ok");
  } catch (error) {
    setStatus(`Помилка: ${error.message}`, "error");
  } finally {
    scanButton.disabled = false;
  }
});

function fillForm(contact) {
  for (const [name, value] of Object.entries(contact)) {
    form.elements[name].value = Array.isArray(value) ? value.join("\n") : value;
  }
}

function readForm() {
  const contact = {};
  for (const element of form.elements) contact[element.name] = element.value.trim();
  contact.phones = contact.phones.split("\n").map((p) => p.trim()).filter((p) => p !== "");
  return contact;
}

// Build .vcf from the (possibly edited) form and save it
downloadButton.addEventListener("click", async () => {
  const contact = readForm();
  const response = await fetch("/api/vcard", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contact),
  });
  if (!response.ok) { setStatus("Не вдалося створити .vcf", "error"); return; }
  const link = document.createElement("a");
  link.href = URL.createObjectURL(await response.blob());
  link.download = (contact.full_name || "contact") + ".vcf";
  link.click();
});
