# Konek - Network Monitor

Konek is a lightweight network monitoring tool that scans your local network for connected devices using ARP table queries. It provides a real-time GUI display of devices, allows custom naming, notification toggles, and runs discreetly in the system tray.

## Features

- **Scanning**: Uses ARP table for instant network device detection (no slow ping sweeps)
- **Real-Time Monitoring**: Automatically scans every 30 seconds for device changes
- **Custom Device Naming**: Assign friendly names to devices for easy identification
- **Notification System**: Get Windows notifications when devices connect/disconnect
- **System Tray Integration**: Minimizes to tray, accessible via double-click or right-click menu
- **Persistent Settings**: Saves device names and notification preferences
- **Cross-Platform GUI**: Built with Tkinter for native Windows appearance

## Requirements

- Python 3.6+
- Windows (for system tray functionality)
- Required packages listed in `requirements.txt`

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

- **Manual**: Double-click `konek.py` or run `python konek.py`
- The application will start minimized in the system tray
- Double-click the tray icon to show the main window
- Right-click the tray icon for menu options

### GUI Features

- **Device List**: Shows IP, custom name, MAC address, and notification status
- **Double-click Name**: Edit custom device names
- **Click Checkbox**: Toggle notifications for device connections/disconnections
- **Quit Button**: Properly closes the application

## Building Standalone Executable

Use PyInstaller to create a standalone executable:

```bash
pyinstaller konek.spec
```

The executable will be created in the `dist` folder.

## Configuration

- Device names and notification settings are automatically saved to `devices.json`
- The application uses `konek.ico` for the tray icon (included)

## How It Works

Konek leverages the Windows ARP cache for lightning-fast device detection. Instead of scanning the entire network range with ping, it queries the existing ARP table which is maintained by the operating system. This provides:

- Instant results (no waiting)
- Low system impact
- Accurate device detection
- Real-time updates

## Troubleshooting

- Ensure Python and required packages are installed
- Run as administrator if ARP access is restricted
- Check Windows Firewall settings for network access
- View console output for debugging information

## License

This project is open source. Feel free to modify and distribute.
