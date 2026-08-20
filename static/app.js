const form = document.getElementById("uploadForm");
const input = document.getElementById("video");
const drop = document.getElementById("drop");
const fileName = document.getElementById("fileName");
const submit = document.getElementById("submit");
const progressBox = document.getElementById("progressBox");
const message = document.getElementById("message");
const percent = document.getElementById("percent");
const bar = document.getElementById("bar");
const result = document.getElementById("result");
const error = document.getElementById("error");

let selectedFile = null;

function setFile(file) {
  if (!file) return;
  selectedFile = file;
  fileName.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
  submit.disabled = false;
  result.classList.add("hidden");
  error.classList.add("hidden");
}

input.addEventListener("change", e => setFile(e.target.files[0]));
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", e => {
  e.preventDefault();
  drop.classList.remove("drag");
  setFile(e.dataTransfer.files[0]);
});

form.addEventListener("submit", async e => {
  e.preventDefault();
  if (!selectedFile) return;

  submit.disabled = true;
  progressBox.classList.remove("hidden");
  result.classList.add("hidden");
  error.classList.add("hidden");
  setProgress(0, "上传视频…");

  const data = new FormData();
  data.append("video", selectedFile);

  try {
    const response = await fetch("/api/upload", { method: "POST", body: data });
    const json = await response.json();
    if (!response.ok) throw new Error(json.error || "上传失败");
    poll(json.job_id);
  } catch (err) {
    showError(err.message);
    submit.disabled = false;
  }
});

async function poll(jobId) {
  try {
    const response = await fetch(`/api/status/${jobId}`);
    const job = await response.json();
    if (!response.ok) throw new Error(job.error || "任务查询失败");

    setProgress(job.progress || 0, job.message || "处理中…");

    if (job.status === "done") {
      result.innerHTML = `✅ ${job.message}<br><a href="${job.download_url}">下载双语字幕视频</a>`;
      result.classList.remove("hidden");
      submit.disabled = false;
      return;
    }
    if (job.status === "error") {
      throw new Error(job.error || "处理失败");
    }

    setTimeout(() => poll(jobId), 1500);
  } catch (err) {
    showError(err.message);
    submit.disabled = false;
  }
}

function setProgress(value, text) {
  bar.style.width = `${value}%`;
  percent.textContent = `${value}%`;
  message.textContent = text;
}

function showError(text) {
  error.textContent = `❌ ${text}`;
  error.classList.remove("hidden");
  progressBox.classList.add("hidden");
}
