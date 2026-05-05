const API_URL = "https://video-cleaner-8j64.onrender.com"

const SUPABASE_URL = "https://mgsngnapsfafydspfmnt.supabase.co"
const SUPABASE_ANON_KEY = "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

let session = null
let selectedFiles = []


window.login = async function () {
  const email = document.getElementById("email").value

  if (!email) {
    alert("Enter email")
    return
  }

  const { error } = await supabaseClient.auth.signInWithOtp({
    email
  })

  if (error) {
    alert(error.message)
    return
  }

  alert("Check your email to login")
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
// AUTH UI
// -------------------------
supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess
  syncUI()
})

function syncUI() {
  const auth = document.getElementById("auth-section")
  const userBox = document.getElementById("user-info")
  const emailInput = document.getElementById("email")
  const userEmail = document.getElementById("user-email")

  const logged = !!session

  if (auth) auth.style.display = logged ? "none" : "block"
  if (userBox) userBox.style.display = logged ? "block" : "none"
  if (emailInput) emailInput.style.display = logged ? "none" : "block"

  if (userEmail && logged) {
    userEmail.innerText = session.user.email
  }
}

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
  if (!container) return

  container.innerHTML = ""

  selectedFiles.forEach((file, i) => {
    const url = URL.createObjectURL(file)

    container.innerHTML += `
      <div class="file-item">
        <div class="video-wrapper">
          <video src="${url}" muted playsinline controls></video>
        </div>
        <button onclick="removeFile(${i})">Remove</button>
      </div>
    `
  })
}

window.removeFile = (i) => {
  selectedFiles.splice(i, 1)
  renderPreviews()
}

// -------------------------
// UPLOAD
// -------------------------
window.upload = async () => {
  if (!selectedFiles.length) {
    alert("No files")
    return
  }

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
    if (data.detail === "GUEST_LIMIT_REACHED") {
      alert("Limit reached. Please login to continue.")
      syncUI()
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
    const res = await fetch(`${API_URL}/status/${jobId}`, {
      headers: {
        Authorization: session ? `Bearer ${session.access_token}` : ""
      }
    })

    const data = await res.json()

    document.getElementById("status").innerText =
      `${data.status || "processing"} ${data.progress ?? 0}%`

    document.getElementById("progress-bar").style.width =
      (data.progress || 0) + "%"

    if (data.status === "done") {
      clearInterval(interval)

      const a = document.getElementById("download")
      a.href = data.output_url
      a.style.display = "block"
      a.innerText = "DOWNLOAD"
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("failed")
    }
  }, 1200)
}
