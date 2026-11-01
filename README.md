# DerMedics AI

Final-year project: a Flutter mobile app and a FastAPI backend for informational skin-health support.

**AI pipeline:** skin image analysis → disease description → medicine suggestions → dermatologist recommendation, with saved reports and PDF export.

```
backend/   FastAPI + SQLAlchemy (PostgreSQL / SQLite), JWT auth, AI pipeline
mobile/    Flutter app (Android, iOS, Web), UI from "DerMedics AI — Flutter Mobile UI.pdf"
ml/        Training script for the skin-disease image classifier
```

## 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then edit values (macOS/Linux: cp)
alembic upgrade head              # create tables
python seed.py                    # sample dermatologists
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs  •  Health: http://localhost:8000/api/health

Tests: `python -m pytest -q`

### Database (PostgreSQL)
Install PostgreSQL, create a database, then set in `backend/.env`:
```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/dermedics
```
Run `alembic upgrade head` and `python seed.py` again. Without Postgres, the default `sqlite:///./dermedics.db` works for development.

Set a long random `JWT_SECRET` before any real use, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### Connecting the language model (Qwen via OpenRouter)
Descriptions and medicine suggestions come from any OpenAI-compatible API. Current setup in `backend/.env`:
```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=qwen/qwen3.7-flash
LLM_FALLBACK_MODELS=google/gemma-4-31b-it:free,nvidia/nemotron-3-super-120b-a12b:free,openrouter/free
```
Models are tried in order. If Qwen fails (for example the account is out of credits), the free models are tried next. If all fail, the curated knowledge base in `backend/app/data/conditions.json` is used, so the app never shows an error. `/api/health` shows `"text_provider": "llm"` when a key is set.

To use Alibaba Model Studio directly instead, set `LLM_BASE_URL` to the base URL shown on your Model Studio API Key page and `LLM_MODEL=qwen-plus`.

### The trained image model
`ml/` trains a MobileNetV3 / EfficientNet classifier on DermNet photos (10 conditions plus an "unsupported" class that the app always reports as inconclusive). The backend serves it with ONNX Runtime.

1. `ml/raw/` holds the DermNet parquet files from Hugging Face (`exper1ment/dermnet`). `python prepare_dermnet.py --per-class 350` builds `ml/data/<label>/`.
2. Train in the Python 3.11 venv (CPU works; about 5 min/epoch on a laptop for MobileNetV3):
   ```bash
   cd ml
   .venv\Scripts\python train.py --data data --epochs 12 --arch mobilenet_v3_large --batch-size 24
   ```
   Keep `--batch-size` at 24 or below with less than 8 GB RAM.
3. Copy `ml/output/skin_model.onnx` and `labels.json` to `backend/models_store/` and set `MODEL_PATH=models_store/skin_model.onnx` (backend needs `pip install -r requirements-ml.txt`).

Without `MODEL_PATH`, a demo classifier returns placeholder results labelled "Illustrative match".

Predictions below `CONFIDENCE_THRESHOLD` (default 0.6) are reported as inconclusive, and the app shows no medicine suggestions for them.

### Dermatologists
Sample providers live in `backend/app/data/seed_dermatologists.json`. Results are ranked by same city, then by whether the provider treats the detected condition, then by distance when device location is used. Set `GOOGLE_PLACES_KEY` to add live Google Places results.

## 2. Mobile app

> **Android phones:** install the ready-made APK from `release/android/`; see [ANDROID.md](ANDROID.md).
>
> **iPhone:** see [IPHONE.md](IPHONE.md). It covers using the app in Safari over Wi-Fi today, or building the real iPhone app in the cloud and installing it from Windows.

```bash
cd mobile
flutter pub get
flutter run                                   # Android emulator uses http://10.0.2.2:8000 automatically
flutter run -d chrome                         # web uses http://localhost:8000
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000   # physical phone on same Wi-Fi
```
Tests: `flutter analyze` and `flutter test`.

**On this PC (7 GB RAM, small C: drive):**
- Build with Gradle's cache on D: using `powershell -File mobile/tool/run_android.ps1 -d <device>` (or `flutter build apk --debug` with `GRADLE_USER_HOME=D:\gradle-home`).
- Use the light **DerMedics_Light** emulator (Android 14, no Play Store, stored in `D:\android-avd`). Close it before building, because the emulator and Gradle together don't fit in RAM. Start it with `emulator -avd DerMedics_Light -no-boot-anim -no-audio`, then `adb install -r mobile/build/app/outputs/flutter-apk/app-debug.apk`.
- The web build is served by `python mobile/tool/serve_web.py` (no-cache, so rebuilds show up on reload).

### Screens
Splash • Login • Register • Confirm email (6-digit code) • Forgot password • Home • Analyze (upload) • Result • Inconclusive • Medicine suggestions • "Who is this scan for?" • Reports • Patient report (styled like the PDF; PDF saves to Android Downloads, the iPhone Files app or the PC's Downloads) • Find nearby care (list/map, device location) • Profile & settings.

### Authentication
- Passwords are hashed with Argon2. The app and API enforce the same strength rules: 8+ characters with upper, lower, digit and symbol.
- Login issues a short-lived JWT access token (15 min) and a refresh token (7 days). Refresh tokens are stored hashed and rotated on every use. Reusing an old refresh token revokes all of that user's sessions.
- Sign-up stores name, email, phone, country and city, then emails a 6-digit code; the account activates only when the code is entered together with the sign-up password. An unconfirmed address can be reclaimed by its real owner.
- Forgot password emails a 6-digit code to the registered address (15 min expiry, 5 tries per code, 60 s resend, 5 codes per hour per account) and tells the user if the email isn't registered.
- Emails are sent from the app's own Gmail account (`SMTP_*` in `backend/.env`, an App Password); without it, codes are written to the server log.
- Login and register are rate-limited (5 per minute per IP), and an account locks for 15 minutes after 10 wrong passwords.
- Logging out revokes the refresh token; changing or resetting the password signs out every device at once.
- Skin and profile photos are served only to their owner through `/api/files/...`; there is no public uploads folder. The app keeps tokens in secure storage (Keychain / Keystore) and refreshes them automatically when a request gets a 401.
- Every analysis, report and PDF is scoped to its owner.

## API summary
| Method | Path | Purpose |
|---|---|---|
| POST | /api/auth/register, /verify-email, /resend-verification | Sign-up with emailed code |
| POST | /api/auth/login, /refresh, /logout | Sign-in and sessions |
| POST | /api/auth/forgot-password, /verify-reset-code, /reset-password | Password reset by emailed code |
| GET/PATCH | /api/auth/me | Profile, phone & region |
| POST/DELETE | /api/auth/me/avatar | Profile photo |
| GET | /api/files/analyses/{name}, /api/files/avatars/{name} | Owner-only photos |
| POST | /api/auth/change-password | Change password |
| POST | /api/analysis | Upload image → full AI pipeline |
| GET | /api/analysis/{id} | Analysis with dermatologist matches |
| POST/GET | /api/reports | Create / list (filter, search) |
| GET/DELETE | /api/reports/{id} | Report detail / delete |
| GET | /api/reports/{id}/pdf | Patient report PDF |
| GET | /api/dermatologists | Search care options |
| GET | /api/dashboard | Home counts + recent activity |

> DerMedics AI is informational only. It does not provide diagnoses or prescriptions.
