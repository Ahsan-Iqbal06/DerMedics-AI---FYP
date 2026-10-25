# Running DerMedics AI on your iPhone XS

Apple only lets iPhone apps be built on a Mac. This project gives you two ways in from a Windows PC:

| | **A. In Safari (works today)** | **B. Real iPhone app (native)** |
|---|---|---|
| Setup time | 2 minutes | ~45 minutes the first time |
| Needs | iPhone + PC on the same Wi-Fi | Free GitHub account, free Apple ID, USB cable, Sideloadly |
| Looks like | Full-screen app from your Home Screen | Normal installed app with the DerMedics icon |
| Limits | PC must be on | PC must be on; free signing must be renewed every 7 days |

In both cases the **backend runs on your PC**, so the PC must be on, with the servers running, and on the same Wi-Fi as the phone.

---

## Start the servers on the PC

Open two PowerShell windows:

```powershell
cd "D:\DerMedics AI FYP\backend"
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```powershell
cd "D:\DerMedics AI FYP\mobile"
python tool\serve_web.py 5173
```

Find the PC's Wi-Fi address with `ipconfig` and look for **IPv4 Address** under *Wireless LAN adapter Wi-Fi*. At the time of writing it is **192.168.18.128**. Home routers can change it, so check again if the phone stops connecting.

> If Windows shows **"Allow access?"** for Python, tick **Private** and **Public** networks and click **Allow**. Your Wi-Fi is currently marked *Public* in Windows.

---

## A. Use it in Safari today

1. On the iPhone, connect to the **same Wi-Fi** as the PC.
2. Open **Safari** and go to **http://192.168.18.128:5173**.
3. Sign in, or create an account. The app automatically talks to the backend on the same PC (port 8000).
4. Tap **Share → Add to Home Screen → Add**. DerMedics now opens full-screen from its own icon.

Photo upload works with **Choose photo** (Photo Library or Take Photo).

---

## B. Install the real iPhone app

### 1. Build the app in the cloud (free Mac from GitHub)

1. Create a free account at **github.com** if you don't have one.
2. Create a **new private repository**, e.g. `dermedics-ai`. Leave *Add a README* **unticked**.
3. In PowerShell, upload the project. The local git repository is already set up and committed:
   ```powershell
   cd "D:\DerMedics AI FYP"
   git remote add origin https://github.com/<your-username>/dermedics-ai.git
   git push -u origin main
   ```
   A browser window opens the first time so you can sign in to GitHub.
   Secrets are **not** uploaded: `backend/.env` (database password, API keys), databases, photos, training data and virtual environments are all excluded by `.gitignore`.
4. On GitHub, open the repository, then go to **Actions**, choose **iOS build (unsigned IPA)**, and click **Run workflow**. Keep the server address as `http://192.168.18.128:8000`, or type your PC's current address, then click **Run workflow**.
5. Wait about 15 minutes for the green tick. Open the run, scroll to **Artifacts** and download **DerMedicsAI-iOS-unsigned**, then unzip it to get **`DerMedicsAI-unsigned.ipa`**.

Private repositories get 2,000 free Actions minutes a month. Mac minutes count 10×, which leaves about 10–12 builds a month. A public repository's builds are free.

### 2. Install it from Windows with Sideloadly

1. On the PC, install **iTunes** and **iCloud**, the versions downloaded from apple.com rather than the Microsoft Store versions, which Sideloadly can't use. Then install **Sideloadly** from **sideloadly.io**.
2. Connect the iPhone XS with a USB cable. Unlock it and tap **Trust This Computer**.
3. Open Sideloadly:
   - drag **`DerMedicsAI-unsigned.ipa`** into it
   - pick your iPhone in **iDevice**
   - enter your **Apple ID** email
   - click **Start** and type your Apple ID password when asked; Sideloadly sends it only to Apple to create the signing certificate. A spare Apple ID works too.
4. On the iPhone:
   - **Settings → Privacy & Security → Developer Mode → On**, then restart when asked and confirm. This option appears after the first install attempt.
   - **Settings → General → VPN & Device Management**, tap your Apple ID, then **Trust**.
5. Open **DerMedics AI** from the Home Screen.

### 3. Point the app at your PC

On the sign-in screen tap **Server: …** at the bottom, enter `192.168.18.128:8000`, tap **Test connection**, then **Save**, and sign in.
Allow **Local Network** access if iOS asks.

### Renewing (free Apple ID)

Apps signed with a free Apple ID **stop opening after 7 days**. To renew, plug the phone in and run Sideloadly again with the same `.ipa`. No rebuild is needed, and your sign-in and settings are kept. A free Apple ID can have up to 3 sideloaded apps at once.

With the **Apple Developer Program** ($99/year) you can instead sign the app for a year or install it through **TestFlight**. That needs signing certificates added to the workflow.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Safari "can't connect" / app says server not reachable | Same Wi-Fi? Both servers running? Re-check the PC's address with `ipconfig`. Allow Python in Windows Firewall. |
| Works at home, not elsewhere | The backend runs on your PC, so the phone must reach it. For use anywhere, deploy the backend online with HTTPS. |
| Sideloadly "Guru Meditation" / login errors | Use the apple.com iTunes and iCloud (not the Store versions) and sign in to iCloud once. Try again after a minute. |
| App won't open, "Untrusted Developer" | Settings → General → VPN & Device Management → Trust. |
| App stopped opening after a week | Free signing expired. Re-run Sideloadly with the same `.ipa`. |
