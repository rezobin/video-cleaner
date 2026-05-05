const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []

// -------------------------
// AUTH
// -------------------------

async function login() {
  const email = document.getElementById("email").value

  await supabaseClient.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: window.location.origin
    }
  })

  alert("Check your email")
}

function logout() {
  supabaseClient.auth.signOut()
}

supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess

  if (session) {
    document.getElementById("user-info").style.display = "block"
    document.getElementById("user-email").innerText = session.user.email

    document.getElementById("email").style.display = "none"
    document.querySelector("button[onclick='login()']").style.display = "none"
  } else {
    document.getElementById("user-info").style.display = "none"

    document.getElementById("email").style.display = "block"
    document.querySelector("button[onclick='login()']").style.display = "block"
  }
})

// -------------------------
// FILE PREVIEW
// -------------------------

document.getElementById("files").addEventListener("change", (e) => {
  selectedFiles = Array.from(e.target.files)
  renderPreviews()
})

function renderPreviews() {
  const container = document.getElementById("preview")
  container.innerHTML = ""

  selectedFiles.forEach((file, index) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")

    div.className = "file-item"
    
    div.innerHTML = `
    <video src="${url}" controls></video>
    <div class="file-actions">
        <button onclick="moveUp(${index})">⬆️</button>
        <button onclick="moveDown(${index})">⬇️</button>
        <button onclick="removeFile(${index})">🗑️</button>
    </div>
    `

    container.appendChild(div)
  })
}

window.removeFile = (i) => {
  selectedFiles.splice(i, 1)
  renderPreviews()
}

window.moveUp = (i) => {
  if (i === 0) return
  ;[selectedFiles[i - 1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i - 1]]
  renderPreviews()
}

window.moveDown = (i) => {
  if (i === selectedFiles.length - 1) return
  ;[selectedFiles[i + 1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i + 1]]
  renderPreviews()
}

// -------------------------
// UPLOAD
// -------------------------

async function upload() {
  if (selectedFiles.length === 0) return alert("no files")

  if (!session) {
    console.log("guest mode")
  }

  const form = new FormData()
  selectedFiles.forEach((f) => form.append("files", f))

  const headers = {}
  if (session) {
    headers["Authorization"] = "Bearer " + session.access_token
  }

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers,
    body: form
  })

  const data = await res.json()

  if (!data.job_id) {
    alert("upload failed")
    return
  }

  poll(data.job_id)
}

// -------------------------
// POLL
// -------------------------

async function poll(jobId) {
  const interval = setInterval(async () => {
    const headers = {}
    if (session) {
      headers["Authorization"] = "Bearer " + session.access_token
    }

    const res = await fetch(`${API_URL}/status/${jobId}`, { headers })
    const data = await res.json()

    document.getElementById("status").innerText = data.status

    // progress bar
    document.getElementById("progress-container").style.display = "block"
    document.getElementById("progress-bar").style.width = (data.progress || 0) + "%"

    if (data.status === "done") {
      clearInterval(interval)

      if (!session) {
        alert("Enter email to download")
        return
      }

      const a = document.getElementById("download")
      a.href = data.output_url
      a.style.display = "block"
      a.innerText = "DOWNLOAD FINAL VIDEO"
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("processing failed")
    }

  }, 1500)
}