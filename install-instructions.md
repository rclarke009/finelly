# Verbiage — Install instructions

Follow these steps once. After that, you’ll start Verbiage from the desktop shortcut.

## Before you start

- **Windows 10 or 11**
- **Docker Desktop** installed and running  
  - If you’re not sure: look for the Docker icon in the system tray (bottom-right). If it’s there and not grayed out, you’re good.  
  - If you don’t have it: install from [docker.com](https://www.docker.com/products/docker-desktop/), then restart the PC if it asks you to.

---

## Step 1: Get the Verbiage ZIP

You should have a file named **Verbiage-Portable.zip** (from a download, USB stick, or email).

---

## Step 2: Unzip it

1. Right-click **Verbiage-Portable.zip**.
2. Click **Extract All…**.
3. Choose a place (e.g. **Desktop** or **Downloads**) and click **Extract**.
4. You’ll get a new folder named **Verbiage** with several files inside, including **Setup.bat**.

---

## Step 3: Run the installer once

1. Open the **Verbiage** folder.
2. Double-click **Setup.bat**.
3. A black window will open and copy files. When it says “Installation complete” and “A Verbiage shortcut is on your desktop,” you’re done.
4. You can close that window. You can also delete the **Verbiage** folder you just unzipped if you like; the app is now installed in a different place.

---

## Step 4: Start Verbiage

1. Make sure **Docker is running** (Docker icon in the system tray).
2. Double-click the **Verbiage** shortcut on your desktop.
3. A window will open; the first time it may take a few minutes to download some data. When it says “Ready” and opens your browser to **http://localhost:8000/**, you’re in.

---

## To stop Verbiage

- Close the black window that opened when you started Verbiage, **or**
- Open **File Explorer**, go to the address bar, type `%LocalAppData%\Verbiage`, press Enter, then double-click **Stop Verbiage** if there’s a shortcut there (or open a Command Prompt in that folder and run: `docker compose down`).

---

## If something goes wrong

- **“Docker is not running”** or the shortcut does nothing useful  
  → Start **Docker Desktop** from the Start menu and wait until its icon in the system tray shows it’s running. Try the shortcut again.

- **The black window closes too fast**  
  → Run **Setup.bat** again from the unzipped Verbiage folder (or from `%LocalAppData%\Verbiage`). It’s safe to run more than once.

- **Browser doesn’t open or the page doesn’t load**  
  → Wait a minute and open your browser yourself. Go to: **http://localhost:8000/**

---

*Verbiage runs on your PC. Your data stays in Docker on this computer unless you change settings.*
