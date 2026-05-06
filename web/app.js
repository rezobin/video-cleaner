const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []
let lastLoginAttempt = 0

// -------------------------
// LOGIN
// -------------------------
window.login = async function () {
  const email = document.getElementById("email")?.value
  if (!email) return alert("Enter email")

  const now = Date.now()
  if (now - lastLoginAttempt < 30000) {
    alert("Wait before retrying")
    return
  }
  lastLoginAttempt = now

  const { error } = await supabaseClient.auth.signInWithOtp({ email })

  if (error) return alert(error.message)

  alert("Check your email")
}

window.logout = async function () {
  await supabaseClient.auth.signOut()
  session = null
}

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
// PREVIEW
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
        <video src="${url}" controls muted></video>
      </div>

      <div class="controls">
        <button onclick="moveUp(${i})">↑</button>
        <button onclick="moveDown(${i})">↓</button>
        <button onclick="removeFile(${i})">✕</button>
      </div>
    `

    container.appendChild(div)
  })
}

window.moveUp = (i) => {
  if (i === 0) return
  [selectedFiles[i-1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i-1]]
  renderPreviews()
}

window.moveDown = (i) => {
  if (i === selectedFiles.length - 1) return
  [selectedFiles[i+1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i+1]]
  renderPreviews()
}

window.removeFile = (i) => {
  selectedFiles.splice(i, 1)
  renderPreviews()
}

// -------------------------
// UPLOAD
// -------------------------
window.upload = async () => {
  if (!selectedFiles.length) return alert("No files")

  setLoading(true)

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
    setLoading(false)
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
    const res = await fetch(`${API_URL}/status/${jobId}`)
    const data = await res.json()

    const status = data.status
    const progress = data.progress ?? 0

    document.getElementById("status").innerText = `${status} ${progress}%`

    const spinner = document.getElementById("spinner")
    spinner.style.display = status === "done" ? "none" : "block"

    document.getElementById("progress-bar").style.width = progress + "%"

    if (status === "done") {
      clearInterval(interval)
      setLoading(false)

      showFinal(data.output_url)
      showActions(data.output_url)
    }

    if (status === "failed") {
      clearInterval(interval)
      setLoading(false)
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
    <button onclick="downloadVideo('${url}')">Download</button>
    <button onclick="shareVideo('${url}')">Share</button>
    <button onclick="newVideo()">New video</button>
  `
}

// -------------------------
// DOWNLOAD (ROBUST)
// -------------------------
window.downloadVideo = (url) => {
  const a = document.createElement("a")
  a.href = url
  a.download = "talklean.mp4"
  a.target = "_blank"
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// -------------------------
// SHARE
// -------------------------
window.shareVideo = async (url) => {
  if (navigator.share) {
    await navigator.share({ url })
  } else {
    window.open(url, "_blank")
  }
}

// -------------------------
// RESET
// -------------------------
window.newVideo = () => {
  location.reload()
}

// -------------------------
// LOADING
// -------------------------
function setLoading(state) {
  const btn = document.getElementById("generate-btn")

  if (state) {
    btn.innerText = "Processing..."
    btn.disabled = true
  } else {
    btn.innerText = "Generate watchable content"
    btn.disabled = false
  }
}