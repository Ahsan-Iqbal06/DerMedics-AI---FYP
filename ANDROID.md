# DerMedics AI on Android phones

Ready-made, signed release APKs are in **`release/android/`**:

| File | Use it for | Size |
|---|---|---|
| `DerMedicsAI-v1.0.6-universal.apk` | **Any Android phone** | 54 MB |

Requires Android 7.0 or newer. Signed with the DerMedics release key, so it installs as an update over 1.0.0 and your
account stays signed in. Smaller per-processor APKs can be built with `--split-per-abi` (see *Rebuilding* below).

**New in 1.0.6:** redesigned patient report and PDF; PDFs save to Downloads/DerMedics AI. From 1.0.5: new accounts confirm their email with a 6-digit code before first sign-in. Also from 1.0.4: skin and profile photos are visible only to their owner, and changing or resetting your password signs out every device immediately. Update from 1.0.3 or older, or photos won't load. (1.0.3 added phone number at sign-up.)

---

## Install on a phone

1. Copy the APK to the phone using any of these:
   - **USB cable:** drag it into the phone's *Download* folder.
   - **Google Drive** or **WhatsApp**: send the file to yourself.
   - **adb:** `adb install release/android/DerMedicsAI-v1.0.6-universal.apk`.
2. On the phone, open the APK with **Files** or **Downloads**.
3. If Android warns about unknown apps, tap **Settings → Allow from this source**, then go back and tap **Install**.
4. If **Play Protect** shows "unrecognised app", tap **More details → Install anyway**. This is normal for apps not from the Play Store.
5. Open **DerMedics AI**.

## Connect it to the backend

The backend runs on your PC, so:

1. On the PC, start the server, listening on the network:
   ```powershell
   cd "D:\DerMedics AI FYP\backend"
   .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Put the phone on the **same Wi-Fi** as the PC.
3. The APK is preset to **`192.168.18.128:8000`**. If your PC's address is different (check with `ipconfig`, *Wireless LAN adapter Wi-Fi → IPv4 Address*), tap **Server: …** at the bottom of the sign-in screen, type the new address, then tap **Test connection** and **Save**.
4. Sign in or create an account.

> If **Test connection** fails: check both devices are on the same Wi-Fi, the backend window is running, and Windows Firewall allows Python. Click **Allow** if Windows asks.

---

## Rebuilding the APKs

From `mobile/`, using the Gradle cache on drive D: because drive C: is nearly full:

```powershell
$env:GRADLE_USER_HOME = "D:\gradle-home"
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.18.128:8000
flutter build apk --release --split-per-abi --dart-define=API_BASE_URL=http://192.168.18.128:8000
```

The output goes to `mobile/build/app/outputs/flutter-apk/`. Close the Android emulator first, because this PC doesn't have enough RAM for both.
Before each new release, raise `version:` in `mobile/pubspec.yaml` (for example `1.0.6+2`) so phones accept it as an update.

### Signing key — keep it safe

- `mobile/android/keystore/dermedics-release.jks` and `mobile/android/key.properties` (which holds its password) sign every release.
- Both are **git-ignored** and exist only on this PC. **Back them up** (for example to a USB drive or private cloud storage).
- If they're lost, future versions can't install as updates over the current one; users would have to uninstall first.
- Without them, release builds fall back to the debug key, which is what happens on GitHub Actions.
