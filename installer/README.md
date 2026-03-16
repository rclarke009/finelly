# Verbiage Windows Installer

Two ways to give Verbiage to someone (e.g. your dad). **Docker Desktop must already be installed** on the target PC.

- **Portable ZIP (Docker-only build)** – No Inno Setup. You build a ZIP with a script that only needs Docker. He unzips and runs `Setup.bat` once.
- **Inno Setup .exe** – Single installer executable; requires Inno Setup 6 on your machine to build.

---

## Option A: Portable ZIP (build with Docker only)

You only need Docker to build. No Inno Setup.

### Build the ZIP

**Mac/Linux** (from project root):
```bash
./installer/build-portable.sh
```

**Windows** (from project root or from `installer`):
```bat
installer\build-portable.bat
```

Output: **`installer/output/Verbiage-Portable.zip`**

### Give it to your dad

1. Send him **Verbiage-Portable.zip** (e.g. USB, cloud, email).
2. He unzips it (e.g. to Desktop or Downloads). He’ll get a folder **Verbiage** with `Setup.bat`, `Start.bat`, etc. inside.
3. He double-clicks **Setup.bat** once. It copies Verbiage to `%LocalAppData%\Verbiage` and creates a **Verbiage** shortcut on the desktop.
4. He can delete the unzipped folder if he likes. To start Verbiage: double-click the desktop shortcut (Docker must be running).

To stop: open a terminal in `%LocalAppData%\Verbiage` and run `docker compose down`, or we could add a Stop Verbiage shortcut later.

---

## Option B: Inno Setup .exe installer

### What the installer does

- Copies the Verbiage app (all files under the project root, except `.env`, `.git`, `__pycache__`, `.venv`, and this `installer/` folder) to `%LocalAppData%\Verbiage`.
- Creates Start Menu entries: **Verbiage** (start), **Stop Verbiage** (run `docker compose down`), and Uninstall.
- Optionally creates a desktop shortcut and a “Start Verbiage now” step at the end of setup.
- No administrator rights required (installs to user’s AppData).

### Building the Inno installer

1. **Install Inno Setup 6** (free): https://jrsoftware.org/isinfo.php  
   - Use the default install; the command-line compiler `iscc` will be on your PATH.

2. **From the project root**, ensure the app folder is complete (Dockerfile, docker-compose.yml, Start.bat, app/, static/, etc.).

3. **Build the installer:**
   ```bat
   cd installer
   iscc verbiage.iss
   ```

4. The resulting executable is:
   - `installer\output\VerbiageSetup.exe`

### Giving it to your dad (Inno)

1. Copy **VerbiageSetup.exe** to his computer (USB, cloud, etc.).
2. He runs **VerbiageSetup.exe** and follows the wizard.
3. He leaves “Start Verbiage now” checked if he wants it to launch right after install (optional).
4. After that, he can start Verbiage anytime from the desktop shortcut or Start Menu → Verbiage → **Verbiage**.  
   To stop: Start Menu → Verbiage → **Stop Verbiage**, or open a terminal in the install folder and run `docker compose down`.

## Requirements on his PC (both options)

- **Windows 10 or 11** (or compatible).
- **Docker Desktop** installed and running. If Docker isn’t installed, the installer will still copy files and create shortcuts, but starting Verbiage will fail until Docker is installed and the PC has been restarted if the installer prompted for it.

## Uninstall

**Inno install:** Use **Settings → Apps → Verbiage → Uninstall**, or run **Uninstall Verbiage** from the Start Menu.

**Portable (Setup.bat) install:** Delete the desktop shortcut and the folder `%LocalAppData%\Verbiage`.

In both cases, Docker and any images/volumes are left as-is (he can remove those separately if desired).
