const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []
let isDone = false

// -------------------------
// INIT
// -------------------------
window.addEventListener("DOMContentLoaded", async () => {
  const { data } = await supabaseClient.auth.getSession()
  session = data.session

  const fileInput = document.getElementById("fileInput")

  fileInput.addEventListener("change", (e) => {
    selectedFiles = [...selectedFiles, ...Array.from(e.target.files || [])]
    renderPreviews()
    e.target.value = ""
  })
})

// -------------------------
// FILE PICKER
// -------------------------
window.openFilePicker = () => {
  document.getElementById("fileInput")?.click()
}

// -------------------------
// PREVIEW (Safari FIXED)
// -------------------------
function renderPreviews() {
  const container = document.getElementById("preview")
  container.innerHTML = ""

  selectedFiles.forEach((file, i) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.className = "file-item"

    div.innerHTML = `
      <div class="video-wrapper">
        <video 
          src="${url}" 
          muted 
          playsinline 
          preload="metadata"
          controls
        ></video>
      </div>
    `

    container.appendChild(div)
  })
}

// -------------------------
// UPLOAD
// -------------------------
window.upload = async () => {
  if (!selectedFiles.length) return alert("No files")

  setUIUploading(true)

  const form = new FormData()
  selectedFiles.forEach(f => form.append("files", f, f.name))

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers: {
      Authorization: session ? `Bearer ${session.access_token}` : ""
    },
    body: form
  })

  const data = await res.json()

  if (!res.ok) {
    setUIUploading(false)
    alert(data.detail || "upload failed")
    return
  }

  showProgress()
  poll(data.job_id)
}

// -------------------------
// POLL
// -------------------------
function poll(jobId) {
  const interval = setInterval(async () => {
    const res = await fetch(`${API_URL}/status/${jobId}`)
    const data = await res.json()

    const status = data.status
    const progress = data.progress ?? 0

    document.getElementById("status").innerText = `${status} ${progress}%`
    document.getElementById("progress-bar").style.width = progress + "%"

    if (status === "done") {
      clearInterval(interval)

      setUIDone()

      const url = data.output_url
      showFinal(url)
      showActions(url)
    }

    if (status === "failed") {
      clearInterval(interval)
      setUIUploading(false)
      alert("failed")
    }
  }, 1000)
}

// -------------------------
// FINAL VIDEO
// -------------------------
function showFinal(url) {
  const video = document.getElementById("final-video")
  video.src = url
  video.style.display = "block"
}

// -------------------------
// ACTIONS
// -------------------------
function showActions(url) {
  const box = document.getElementById("action-box")

  box.innerHTML = `
    <button class="primary" onclick="downloadVideo('${url}')">Download</button>
    <button class="primary" onclick="shareVideo('${url}')">Share</button>
    <button class="primary" onclick="newVideo()">New video</button>
  `
}

// -------------------------
// DOWNLOAD FIX (REAL)
// -------------------------
window.downloadVideo = async (url) => {
  const res = await fetch(url)
  const blob = await res.blob()

  const blobUrl = URL.createObjectURL(blob)

  const a = document.createElement("a")
  a.href = blobUrl
  a.download = "talklean.mp4"
  document.body.appendChild(a)
  a.click()
  a.remove()

  URL.revokeObjectURL(blobUrl)
}

// -------------------------
// SHARE (REALISTIC LIMIT)
// -------------------------
window.shareVideo = async (url) => {
  if (navigator.share) {
    try {
      await navigator.share({ url })
    } catch {}
  } else {
    window.open(url, "_blank")
  }
}

// -------------------------
// NEW PROJECT
// -------------------------
window.newVideo = () => location.reload()

// -------------------------
// UI STATES
// -------------------------
function setUIUploading(state) {
  const btn = document.getElementById("generate-btn")
  const select = document.getElementById("fileInput")
  const label = document.querySelector(".file-btn")

  if (state) {
    btn.disabled = true
    btn.innerText = "Processing..."
    document.getElementById("progress-container").style.display = "block"
  } else {
    btn.disabled = false
    btn.innerText = "Generate watchable content"
  }
}

function setUIDone() {
  isDone = true

  document.getElementById("generate-btn").style.display = "none"
  document.querySelector(".file-btn").style.display = "none"
  document.getElementById("preview").style.display = "none"
  document.getElementById("progress-container").style.display = "none"
  document.getElementById("spinner").style.display = "none"
}

function showProgress() {
  document.getElementById("progress-container").style.display = "block"
}