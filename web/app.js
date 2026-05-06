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
  const email = document.getElementById("email").value
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
  syncUI()
}

// -------------------------
// INIT
// -------------------------
window.addEventListener("DOMContentLoaded", async () => {
  const { data } = await supabaseClient.auth.getSession()
  session = data.session

  syncUI()

  const fileInput = document.getElementById("fileInput")

  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    selectedFiles = selectedFiles.concat(files)
    renderPreviews()

    e.target.value = ""
  })
})

// -------------------------
// AUTH STATE
// -------------------------
supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess
  syncUI()
})

function syncUI() {
  const auth = document.getElementById("auth-section")
  const userBox = document.getElementById("user-info")
  const emailInput = document.getElementById("email")

  const logged = !!session

  if (auth) auth.style.display = logged ? "none" : "block"
  if (userBox) userBox.style.display = logged ? "block" : "none"
  if (emailInput) emailInput.style.display = logged ? "none" : "block"

  updateUserUI()
}

// -------------------------
// FILE PICKER
// -------------------------
window.openFilePicker = () => {
  document.getElementById("fileInput")?.click()
}

// -------------------------
// PREVIEW + ORDER
// -------------------------
function renderPreviews() {
  const container = document.getElementById("preview")
  if (!container) return

  const scrollY = window.scrollY
  container.innerHTML = ""

  selectedFiles.forEach((file, index) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.className = "file-item"

    div.innerHTML = `
      <div class="video-wrapper">
        <video src="${url}" muted playsinline controls></video>
      </div>

      <div style="display:flex;gap:6px;justify-content:center;margin-top:8px;">
        <button type="button" onclick="moveUp(${index})">↑</button>
        <button type="button" onclick="moveDown(${index})">↓</button>
        <button type="button" onclick="removeFile(${index})">✕</button>
      </div>
    `

    container.appendChild(div)
  })

  window.scrollTo(0, scrollY)
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

window.removeFile = (i) => {
  selectedFiles.splice(i, 1)
  renderPreviews()
}

// -------------------------
// UPLOAD (FIX IMPORTANT)
// -------------------------
window.upload = async () => {
  if (!selectedFiles.length) return alert("No files")

  const form = new FormData()

  selectedFiles.forEach(f => {
    form.append("files", f, f.name)
  })

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers: {
      Authorization: session ? `Bearer ${session.access_token}` : ""
    },
    body: form
  })

  const data = await res.json()

  if (!res.ok) {
    if (data.detail === "GUEST_LIMIT_REACHED") {
      alert("Limit reached. Please login.")
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

    const status = data.status || "processing"
    const progress = data.progress ?? 0

    document.getElementById("status").innerText =
      `${status} ${progress}%`

    document.getElementById("progress-container").style.display = "block"
    document.getElementById("progress-bar").style.width = progress + "%"

    if (status === "done") {
      clearInterval(interval)

      const url = data.output_url
      if (!url) return

      showFinalVideo(url)
      attachDownloadButton(url)
    }

    if (status === "failed") {
      clearInterval(interval)
      alert("failed")
    }
  }, 1000)
}

// -------------------------
// FINAL VIDEO
// -------------------------
function showFinalVideo(url) {
  let video = document.getElementById("final-video")

  if (!video) {
    video = document.createElement("video")
    video.id = "final-video"
    video.controls = true
    video.style.width = "100%"
    video.style.marginTop = "16px"

    document.querySelector(".container").appendChild(video)
  }

  video.src = url
}

// -------------------------
// DOWNLOAD BUTTON (UNIVERSAL FIX)
// -------------------------
function attachDownloadButton(url) {
  let btn = document.getElementById("download-btn")

  if (!btn) {
    btn = document.createElement("button")
    btn.id = "download-btn"
    btn.className = "primary"
    btn.innerText = "Download video"

    document.querySelector(".container").appendChild(btn)
  }

  btn.onclick = () => downloadVideo(url)
}

// -------------------------
// FORCE DOWNLOAD (ALL DEVICES)
// -------------------------
window.downloadVideo = function (url) {
  const a = document.createElement("a")
  a.href = url
  a.download = "talklean.mp4"
  a.target = "_blank"

  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// -------------------------
// USER UI
// -------------------------
function updateUserUI() {
  const userEmail = document.getElementById("user-email")

  if (session?.user && userEmail) {
    userEmail.innerText = `Welcome, ${session.user.email}`
  }
}