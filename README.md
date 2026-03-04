# ETA Heating (Pellematic) for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/github/v/release/Patzgge/homeassistant-eta-pellematic?include_prereleases)](https://github.com/Patzgge/homeassistant-eta-pellematic/releases)

A modern, asynchronous Home Assistant integration for **ETA Heating Systems** (Pellematic, PU, PC, SH, etc.).

Unlike older integrations, this component features **Auto-Discovery**. It connects to your ETA boiler, crawls the entire menu structure via the REST API, and automatically creates sensors for all available data points (temperatures, pressures, status messages, pellet bin content, etc.).

## ✨ Features

* **Auto-Discovery:** No manual configuration of URIs needed. The integration crawls your specific system layout.
* **Smart Naming:** Automatically generates clean names (e.g., "Kessel Rücklauf") and removes duplicate folder names.
* **Data Types:** Correctly handles Numbers (Temperature, Weight) and Text (Status messages like "Bereit" or "Heizen").
* **Modern Backend:** Uses Home Assistant's `DataUpdateCoordinator` for efficient fetching.
* **Performance:** Uses asynchronous requests with concurrency limits to be fast but gentle on the ETA controller's CPU.

## 📋 Prerequisites

Before installing, you **must enable the REST API** on your ETA Touch Display:

1.  Go to your ETA boiler screen.
2.  Log in/Switch to **Service** or **Profi** user mode (often requires a password, check your manual).
3.  Go to **System Settings** -> **Network** (or "Internet").
4.  Enable **RESTful Web Services** (or "Webservice").
5.  Note down the **IP Address** of the boiler.

*Tip: You can test if it works by opening `http://<YOUR_IP>:8080/user/menu` in your browser. If you see XML code, you are ready.*

## 🚀 Installation via HACS

1.  Open **HACS** in Home Assistant.
2.  Go to **Integrations**.
3.  Click the **three dots** in the top right corner -> **Custom repositories**.
4.  Paste the URL of this repository:
    `https://github.com/Patzgge/homeassistant-eta-pellematic`
5.  Select Category: **Integration**.
6.  Click **Add**.
7.  Search for **ETA Heating** and install it.
8.  **Restart Home Assistant**.

## ⚙️ Configuration

1.  Go to **Settings** -> **Devices & Services**.
2.  Click **+ Add Integration**.
3.  Search for **ETA Heating**.
4.  Enter the **IP Address** and **Port** (Default: 8080).
5.  Click Submit. The system will now scan your boiler (this might take a few seconds) and add all sensors.

## ❓ FAQ

**Q: I have thousands of sensors, is this normal?**
A: ETA systems expose almost every internal variable. You can disable the ones you don't need in Home Assistant, but the integration finds everything available in the user menu.

**Q: The sensor names are in German?**
A: The integration reads the names directly from the boiler's firmware. If your installer set up the boiler in German, the API returns German names.

**Q: Can I change values (e.g., turn heating on/off)?**
A: Currently, this integration is Read-Only to ensure safety. Write support is planned for future releases.

## Disclaimer

This is a custom integration and not affiliated with ETA Heiztechnik GmbH. Use at your own risk.
