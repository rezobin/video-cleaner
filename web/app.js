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
      // IMPORTANT: production-safe redirect
      emailRedirectTo: window.location.origin
    }
  })

  alert("Check your email")
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
// FILE PREVIEW + STATE
// -------------------------

document.getElementById("files").addEventListener("change", (e) => {
  selectedFiles = Array.from(e.target.files)
  renderPreviews()
})

function renderPreviews() {
  const container = document.getElementById("preview")
  if (!container) return

  container.innerHTML = ""

  selectedFiles.forEach((file, index) => {
    const url = URL.createObjectURL(file)

    const div = document.createElement("div")
    div.style.margin = "10px"
    div.style.border = "1px solid #ccc"
    div.style.padding = "10px"

    div.innerHTML = `
      <video src="${url}" controls style="max-width:200px;border-radius:10px"></video>
      <div>
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
  [selectedFiles[i - 1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i - 1]]
  renderPreviews()
}

window.moveDown = (i) => {
  if (i === selectedFiles.length - 1) return
  [selectedFiles[i + 1], selectedFiles[i]] = [selectedFiles[i], selectedFiles[i + 1]]
  renderPreviews()
}

// -------------------------
// UPLOAD
// -------------------------

async function upload() {
  if (!session) return alert("login first")
  if (selectedFiles.length === 0) return alert("no files")

  const form = new FormData()

  selectedFiles.forEach((f) => {
    form.append("files", f)
  })

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + session.access_token
    },
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
// POLL STATUS
// -------------------------

function setProgress(p) {
  document.getElementById("progress-container").style.display = "block"
  document.getElementById("progress-bar").style.width = p + "%"
}

async function poll(jobId) {
  const interval = setInterval(async () => {

    const res = await fetch(`${API_URL}/status/${jobId}`, {
      headers: {
        "Authorization": "Bearer " + session.access_token
      }
    })

    const data = await res.json()

    console.log("[STATUS]", data)

    document.getElementById("status").innerText = data.status

    setProgress(data.progress || 0)

    if (data.status === "done") {
      clearInterval(interval)

      const a = document.getElementById("download")

      if (data.output_url) {
        a.href = data.output_url
      } else {
        console.error("NO OUTPUT URL")
      }

      a.style.display = "block"
      a.innerText = "DOWNLOAD FINAL VIDEO"
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("processing failed")
    }

  }, 1500)
}

