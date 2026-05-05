const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []

// -------------------------
// AUTH
// -------------------------
supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess

  const userBox = document.getElementById("user-info")
  const emailInput = document.getElementById("email")

  if (userBox) userBox.style.display = session ? "block" : "none"
  if (emailInput) emailInput.style.display = session ? "none" : "block"
})

// -------------------------
// GLOBAL FILE PICKER (FIX TRY NOW)
// -------------------------
window.openFilePicker = function () {
  const input = document.getElementById("fileInput")
  if (!input) {
    console.error("fileInput missing")
    return
  }
  input.click()
}

// -------------------------
// FILE INPUT (SINGLE SOURCE OF TRUTH)
// -------------------------
document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput")

  if (!fileInput) {
    console.error("fileInput NOT FOUND")
    return
  }

  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files || [])

    if (!files.length) return

    // replace state (important)
    selectedFiles = files

    renderPreviews()

    // allow reselect same files
    e.target.value = ""
  })
})

// -------------------------
// PREVIEW
// -------------------------
function renderPreviews() {
  const container = document.getElementById("preview")
  if (!container) return

  container.innerHTML = ""

  console.log("renderPreviews:", selectedFiles.length)

  selectedFiles.forEach((file, index) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.className = "file-item"

    div.innerHTML = `
      <div class="video-wrapper">
        <video muted playsinline autoplay loop src="${url}"></video>
      </div>

      <div style="display:flex;gap:6px;justify-content:center;margin-top:6px;">
        <button onclick="moveUp(${index})">↑</button>
        <button onclick="moveDown(${index})">↓</button>
        <button onclick="removeFile(${index})">✕</button>
      </div>
    `

    container.appendChild(div)
  })
}

// -------------------------
// FILE OPS
// -------------------------
window.removeFile = function (i) {
  selectedFiles.splice(i, 1)
  renderPreviews()
}

window.moveUp = function (i) {
  if (i === 0) return
  [selectedFiles[i - 1], selectedFiles[i]] =
    [selectedFiles[i], selectedFiles[i - 1]]
  renderPreviews()
}

window.moveDown = function (i) {
  if (i === selectedFiles.length - 1) return
  [selectedFiles[i + 1], selectedFiles[i]] =
    [selectedFiles[i], selectedFiles[i + 1]]
  renderPreviews()
}

// -------------------------
// UPLOAD (GUARD FIX)
// -------------------------
window.upload = async function () {
  if (!selectedFiles || selectedFiles.length === 0) {
    alert("Choose files first")
    return
  }

  const form = new FormData()

  selectedFiles.forEach(f => form.append("files", f))

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers: {
      "Authorization": session ? "Bearer " + session.access_token : ""
    },
    body: form
  })

  const data = await res.json()

  if (!data.job_id) {
    alert(data.detail || "upload failed")
    return
  }

  poll(data.job_id)
}

// -------------------------
// POLL
// -------------------------
function poll(jobId) {
  const interval = setInterval(async () => {
    const res = await fetch(`${API_URL}/status/${jobId}`, {
      headers: {
        "Authorization": session ? "Bearer " + session.access_token : ""
      }
    })

    const data = await res.json()

    const statusEl = document.getElementById("status")
    const bar = document.getElementById("progress-bar")
    const container = document.getElementById("progress-container")

    if (statusEl) {
      statusEl.innerText = `${data.status} ${data.progress || 0}%`
    }

    if (container) container.style.display = "block"
    if (bar) bar.style.width = (data.progress || 0) + "%"

    if (data.status === "done") {
      clearInterval(interval)

      const a = document.getElementById("download")
      if (a) {
        a.href = data.output_url
        a.style.display = "block"
        a.innerText = "DOWNLOAD FINAL VIDEO"
      }
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("processing failed")
    }

  }, 1200)
}