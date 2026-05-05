const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// -------------------------
// STATE
// -------------------------
let session = null
let selectedFiles = []

// -------------------------
// INIT UI ON LOAD
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

    // important: allow re-select same files
    e.target.value = ""
  })
})

// -------------------------
// AUTH STATE CHANGE
// -------------------------
supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess

  const auth = document.getElementById("auth-section")
  const userBox = document.getElementById("user-info")
  const emailInput = document.getElementById("email")

  if (!auth) return

  if (session) {
    auth.style.display = "none"
    if (userBox) userBox.style.display = "block"
    if (emailInput) emailInput.style.display = "none"
  } else {
    auth.style.display = "block"
    if (userBox) userBox.style.display = "none"
    if (emailInput) emailInput.style.display = "block"
  }
})

supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess

  const userBox = document.getElementById("user-info")
  const authSection = document.getElementById("auth-section")

  if (userBox) userBox.style.display = session ? "block" : "none"
  if (authSection) authSection.style.display = session ? "none" : "block"
})
// -------------------------
// UI SYNC (IMPORTANT FIX)
// -------------------------
function syncUI() {
  const authSection = document.getElementById("auth-section")
  const userBox = document.getElementById("user-info")
  const emailInput = document.getElementById("email")
  const userEmail = document.getElementById("user-email")

  const isLogged = !!session

  if (authSection) {
    authSection.style.display = isLogged ? "none" : "block"
  }

  if (userBox) {
    userBox.style.display = isLogged ? "block" : "none"
  }

  if (emailInput) {
    emailInput.style.display = isLogged ? "none" : "block"
  }

  if (userEmail && isLogged) {
    userEmail.innerText = session.user.email
  }
}

// -------------------------
// FILE PICKER (TRY NOW FIX)
// -------------------------
window.openFilePicker = function () {
  const input = document.getElementById("fileInput")
  if (!input) return console.error("fileInput missing")
  input.click()
}

// -------------------------
// PREVIEWS
// -------------------------
function renderPreviews() {
  const container = document.getElementById("preview")
  if (!container) return

  container.innerHTML = ""

  selectedFiles.forEach((file, index) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.className = "file-item"

    div.innerHTML = `
      <div class="video-wrapper">
        <video src="${url}" muted playsinline controls></video>
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
// UPLOAD
// -------------------------
window.upload = async function () {
  if (!selectedFiles.length) {
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

  // 🔴 CAS IMPORTANT
  if (!res.ok) {
    if (data.detail === "GUEST_LIMIT_REACHED") {
      alert("Limit reached (2 uploads). Please login to continue.")
      document.getElementById("auth-section").style.display = "block"
      return
    }

    alert(data.detail || "upload failed")
    return
  }

  poll(data.job_id)
}
// -------------------------
// POLLING
// -------------------------
function poll(jobId) {
  const interval = setInterval(async () => {
    const res = await fetch(`${API_URL}/status/${jobId}`, {
      headers: {
        "Authorization": session ? "Bearer " + session.access_token : ""
      }
    })

    const data = await res.json()

    document.getElementById("status").innerText =
    `${data.status || "processing"} ${data.progress ?? 0}%`

    document.getElementById("progress-container").style.display = "block"
    document.getElementById("progress-bar").style.width =
      (data.progress || 0) + "%"

    if (data.status === "done") {
      clearInterval(interval)

      const a = document.getElementById("download")
      const url = data.output_url || data.url
      a.style.display = "block"
      a.innerText = "DOWNLOAD FINAL VIDEO"
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("processing failed")
    }
  }, 1200)
}