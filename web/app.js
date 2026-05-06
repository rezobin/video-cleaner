const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []

// -------------------------
// INIT
// -------------------------
window.addEventListener("DOMContentLoaded", async () => {
  const { data } = await supabaseClient.auth.getSession()
  session = data.session
  syncUI()

  const fileInput = document.getElementById("fileInput")

  fileInput.addEventListener("change", (e) => {
    selectedFiles = [...selectedFiles, ...Array.from(e.target.files)]
    renderPreviews()
    e.target.value = ""
  })
})

// -------------------------
// AUTH STATE CHANGE
// -------------------------
supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess
  syncUI()

  // 🔥 débloque bouton après login
  if (sess) {
    const btn = document.getElementById("generate-btn")
    if (btn) btn.disabled = false
  }
})

// -------------------------
// AUTH UI
// -------------------------
function syncUI() {
  const auth = document.getElementById("auth-section")
  const userBox = document.getElementById("user-info")
  const userEmail = document.getElementById("user-email")

  if (!auth || !userBox || !userEmail) return

  const logged = !!session

  auth.style.display = logged ? "none" : "block"
  userBox.style.display = logged ? "block" : "none"

  if (logged && session.user) {
    userEmail.innerText = "Connected as " + session.user.email
  }
}

// -------------------------
window.login = async () => {
  const email = document.getElementById("email").value
  if (!email) return alert("Enter email")

  const { error } = await supabaseClient.auth.signInWithOtp({ email })
  if (error) return alert(error.message)

  alert("Check email")
}

window.logout = async () => {
  await supabaseClient.auth.signOut()
  session = null
  syncUI()
}

// -------------------------
// LOGIN GATE (🔥 IMPORTANT)
// -------------------------
function showLoginGate() {
  document.getElementById("status").innerText =
    "Free limit reached — login to continue"

  const auth = document.getElementById("auth-section")
  if (auth) {
    auth.style.display = "block"
    auth.scrollIntoView({ behavior: "smooth" })
  }

  const btn = document.getElementById("generate-btn")
  if (btn) btn.disabled = true
}

// -------------------------
// FILE PICKER
// -------------------------
window.openFilePicker = () => {
  document.getElementById("fileInput").click()
}

// -------------------------
// PREVIEW (WITH SCROLL FIX)
// -------------------------
function renderPreviews() {
  const container = document.getElementById("preview")
  const scrollY = window.scrollY

  container.innerHTML = ""

  selectedFiles.forEach((file, i) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.className = "file-item"

    div.innerHTML = `
      <div class="video-wrapper">
        <video src="${url}" playsinline muted controls></video>
      </div>

      <div class="controls">
        <button onclick="moveUp(${i})">↑</button>
        <button onclick="moveDown(${i})">↓</button>
        <button onclick="removeFile(${i})">✕</button>
      </div>
    `

    container.appendChild(div)
  })

  window.scrollTo(0, scrollY)
}

window.moveUp = (i) => {
  if (i === 0) return
  ;[selectedFiles[i-1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i-1]]
  renderPreviews()
}

window.moveDown = (i) => {
  if (i === selectedFiles.length - 1) return
  ;[selectedFiles[i+1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i+1]]
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

  document.getElementById("status-row").style.display = "flex"
  document.getElementById("progress-container").style.display = "block"

  setLoading(true)

  const form = new FormData()
  selectedFiles.forEach(f => form.append("files", f))

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

    if (data.detail === "GUEST_LIMIT_REACHED") {
      showLoginGate() // 🔥 REPLACE ALERT
      return
    }

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
    document.getElementById("progress-bar").style.width = progress + "%"

    if (status === "done") {
      clearInterval(interval)
      setLoading(false)

      showFinal(data.output_url)
      showActions(data.output_url)
      hideUploadUI()
    }

    if (status === "failed") {
      clearInterval(interval)
      setLoading(false)
      alert("Processing failed")
    }

  }, 1000)
}

// -------------------------
// FINAL
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
  document.getElementById("action-box").innerHTML = `
    <button class="cta" onclick="downloadVideo('${url}')">Download</button>
    <button class="cta" onclick="shareVideo('${url}')">Share</button>
    <button class="cta" onclick="newVideo()">New</button>
  `
}

// -------------------------
// HIDE UI
// -------------------------
function hideUploadUI() {
  document.getElementById("generate-btn").style.display = "none"
  document.getElementById("fileInput").style.display = "none"
  document.getElementById("select-btn").style.display = "none"
  document.getElementById("preview").style.display = "none"
}

// -------------------------
// DOWNLOAD
// -------------------------
window.downloadVideo = async (url) => {
  try {
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
  } catch {
    window.open(url)
  }
}

// -------------------------
// SHARE
// -------------------------
window.shareVideo = async (url) => {
  if (navigator.share) {
    await navigator.share({ url })
  } else {
    window.open(url)
  }
}

// -------------------------
window.newVideo = () => location.reload()

function setLoading(state) {
  const btn = document.getElementById("generate-btn")
  btn.disabled = state
  btn.innerText = state ? "Processing..." : "Generate watchable content"
}