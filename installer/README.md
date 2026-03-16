# Finelly Windows Installer

Two ways to give Finelly to someone (e.g. your dad). **Docker Desktop must already be installed** on the target PC.

- **Portable ZIP (Docker-only build)** – No Inno Setup. You build a ZIP with a script that only needs Docker. He unzips and runs `Setup.bat` once.
- **Inno Setup .exe** – Single installer executable; requires Inno Setup 6 on your machine to build.

---

## Option A: Portable ZIP (build with Docker only)

You only need Docker to build. No Inno Setup.

### Build the ZIP

**Mac/Linux** (from repo root):
```bash
./finelly/installer/build-portable.sh
```

**Windows** (from repo root or from `finelly\installer`):
```bat
finelly\installer\build-portable.bat
```

Output: **`finelly/installer/output/Finelly-Portable.zip`**

### Give it to your dad

1. Send him **Finelly-Portable.zip** (e.g. USB, cloud, email).
2. He unzips it (e.g. to Desktop or Downloads). He’ll get a folder **Finelly** with `Setup.bat`, `Start.bat`, etc. inside.
3. He double-clicks **Setup.bat** once. It copies Finelly to `%LocalAppData%\Finelly` and creates a **Finelly** shortcut on the desktop.
4. He can delete the unzipped folder if he likes. To start Finelly: double-click the desktop shortcut (Docker must be running).

To stop: open a terminal in `%LocalAppData%\Finelly` and run `docker compose down`, or we could add a Stop Finelly shortcut later.

---

## Option B: Inno Setup .exe installer

### What the installer does

- Copies the Finelly app (all files under `finelly/`, except `.env`, `.git`, `__pycache__`, `.venv`, and this `installer/` folder) to `%LocalAppData%\Finelly`.
- Creates Start Menu entries: **Finelly** (start), **Stop Finelly** (run `docker compose down`), and Uninstall.
- Optionally creates a desktop shortcut and a “Start Finelly now” step at the end of setup.
- No administrator rights required (installs to user’s AppData).

### Building the Inno installer

1. **Install Inno Setup 6** (free): https://jrsoftware.org/isinfo.php  
   - Use the default install; the command-line compiler `iscc` will be on your PATH.

2. **From the repo root**, ensure the `finelly` folder is complete (Dockerfile, docker-compose.yml, Start.bat, app/, static/, etc.).

3. **Build the installer:**
   ```bat
   cd finelly\installer
   iscc finelly.iss
   ```

4. The resulting executable is:
   - `finelly\installer\output\FinellySetup.exe`

### Giving it to your dad (Inno)

1. Copy **FinellySetup.exe** to his computer (USB, cloud, etc.).
2. He runs **FinellySetup.exe** and follows the wizard.
3. He leaves “Start Finelly now” checked if he wants it to launch right after install (optional).
4. After that, he can start Finelly anytime from the desktop shortcut or Start Menu → Finelly → **Finelly**.  
   To stop: Start Menu → Finelly → **Stop Finelly**, or open a terminal in the install folder and run `docker compose down`.

## Requirements on his PC (both options)

- **Windows 10 or 11** (or compatible).
- **Docker Desktop** installed and running. If Docker isn’t installed, the installer will still copy files and create shortcuts, but starting Finelly will fail until Docker is installed and the PC has been restarted if the installer prompted for it.

## Uninstall

**Inno install:** Use **Settings → Apps → Finelly → Uninstall**, or run **Uninstall Finelly** from the Start Menu.

**Portable (Setup.bat) install:** Delete the desktop shortcut and the folder `%LocalAppData%\Finelly`.

In both cases, Docker and any images/volumes are left as-is (he can remove those separately if desired).
