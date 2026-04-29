const API_URL = "https://video-cleaner-8j64.onrender.com"

const supabaseClient = supabase.createClient(
  "https://mgsngnapsfafydspfmnt.supabase.co",
  "sb_publishable_DGfn4J71yW2U6oY7beHGDg_Wptvc0Wy"
)

let session = null

// ---------------- AUTH ----------------

async function login() {
  const email = document.getElementById("email").value

  await supabaseClient.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: window.location.origin
    }
  })

  alert("check email")
}

supabaseClient.auth.onAuthStateChange((_, sess) => {
  session = sess
})

// ---------------- UPLOAD ----------------

async function upload() {

  if (!session) return alert("login first")

  const files = document.getElementById("files").files
  const form = new FormData()

  for (let f of files) {
    form.append("files", f)
  }

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + session.access_token
    },
    body: form
  })

  const data = await res.json()

  poll(data.job_id)
}

// ---------------- POLL ----------------

async function poll(jobId) {

  const interval = setInterval(async () => {

    const res = await fetch(`${API_URL}/status/${jobId}`, {
      headers: {
        "Authorization": "Bearer " + session.access_token
      }
    })

    const data = await res.json()

    document.getElementById("status").innerText = data.status

    if (data.status === "done") {
      clearInterval(interval)

      const a = document.getElementById("download")
      a.href = `${API_URL}/download/${jobId}`
      a.style.display = "block"
    }

    if (data.status === "failed") {
      clearInterval(interval)
      alert("failed")
    }

  }, 1500)
}