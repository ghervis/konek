#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import subprocess
import re
from datetime import datetime
import json
import os
import queue
import sys
import win32api
import win32con
import win32gui
from plyer import notification


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class UltraFastMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Konek")
        self.root.geometry("700x350")

        self.device_list = []
        self.previous_devices = []
        self.saved_devices = self.load_saved_devices()
        self.tray_queue = queue.Queue()
        self.create_gui()
        self.create_tray_icon()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.withdraw()
        self.send_notification("Konek", "Konek is running in the system tray")
        # Auto-scan on startup
        self.root.after(1000, self.ultra_fast_scan)
        # Start tray queue checker
        self.check_tray_queue()

    def load_saved_devices(self):
        """Load saved device data from file"""
        try:
            if os.path.exists('devices.json'):
                with open('devices.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.log_message(f"Error loading saved devices: {e}")
        return {}

    def save_devices(self):
        """Save device data to file"""
        try:
            with open('devices.json', 'w') as f:
                json.dump(self.saved_devices, f, indent=4)
        except Exception as e:
            self.log_message(f"Error saving devices: {e}")

    def create_gui(self):
        """Create the GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Device list frame
        self.list_frame = ttk.LabelFrame(main_frame, text="0 Connected Devices", padding="5")
        self.list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Create treeview for devices
        columns = ("IP", "Custom Name", "MAC", "Notify")
        self.device_tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", height=15)

        # Define column headings
        self.device_tree.heading("IP", text="IP")
        self.device_tree.column("IP", width=150)
        self.device_tree.heading("Custom Name", text="Custom Name")
        self.device_tree.column("Custom Name", width=150)
        self.device_tree.heading("MAC", text="MAC")
        self.device_tree.column("MAC", width=200)
        self.device_tree.heading("Notify", text="Notify")
        self.device_tree.column("Notify", width=80, anchor='center')

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=scrollbar.set)

        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to edit custom name
        self.device_tree.bind("<Double-1>", self.edit_custom_name)
        # Bind single-click to toggle notify
        self.device_tree.bind("<Button-1>", self.toggle_notify)

        # Add quit button
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, pady=5)
        self.quit_button = ttk.Button(self.button_frame, text="Quit", command=self.quit_app)
        self.quit_button.pack(side=tk.RIGHT)


    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def send_notification(self, title, message):
        """Send Windows notification"""
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Ultra-Fast Monitor",
                timeout=5
            )
        except Exception as e:
            self.log_message(f"Failed to send notification: {e}")

    def check_device_changes(self, new_devices):
        """Check for device connections/disconnections and send notifications"""
        if not self.previous_devices:
            return  # First scan, no notifications

        # Create sets of IPs for comparison
        previous_ips = {d['ip'] for d in self.previous_devices}
        new_ips = {d['ip'] for d in new_devices}

        # Find new devices
        new_device_ips = new_ips - previous_ips
        # Find disconnected devices
        gone_device_ips = previous_ips - new_ips

        # Send notifications for new devices
        for ip in new_device_ips:
            device = next((d for d in new_devices if d['ip'] == ip), None)
            if device and device['notify']:
                self.send_notification("Device Connected", f"{device['custom_name']} ({ip}) connected to network")


    def is_network_infrastructure(self, ip):
        """Check if IP is network infrastructure (not a real device)"""
        # Network and broadcast addresses
        if ip.endswith('.0') or ip.endswith('.255'):
            return True

        # Common gateway/router addresses
        if ip.endswith('.1'):
            return True

        # Global broadcast
        if ip == '255.255.255.255':
            return True

        return False

    def extract_mac_address(self, line):
        """Extract MAC address from ARP output line with improved detection"""
        # Try multiple MAC address patterns
        patterns = [
            r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}',  # Standard format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
            r'([0-9A-Fa-f]{2}[-]){5}[0-9A-Fa-f]{2}',   # Hyphen format: XX-XX-XX-XX-XX-XX
            r'([0-9A-Fa-f]{2}[:]){5}[0-9A-Fa-f]{2}',   # Colon format: XX:XX:XX:XX:XX:XX
            r'([0-9A-Fa-f]{2}[.]){5}[0-9A-Fa-f]{2}',   # Dot format: XX.XX.XX.XX.XX.XX
            r'([0-9A-Fa-f]{4}[.]){2}[0-9A-Fa-f]{4}',   # Cisco format: XXXX.XXXX.XXXX
        ]

        for pattern in patterns:
            mac_match = re.search(pattern, line)
            if mac_match:
                return mac_match.group(0).upper()

        return None


    def ultra_fast_scan(self):
        """Ultra-fast scan using ARP table only"""
        self.log_message("Starting ultra-fast ARP scan...")

        try:
            # Get ARP table - this is INSTANT
            result = subprocess.run('arp -a', shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                devices = self.parse_arp_output(result.stdout)
                self.check_device_changes(devices)
                self.device_list = devices
                self.previous_devices = devices[:]
                self.update_display()
                self.log_message(f"Scan completed - Found {len(devices)} devices")
                # Schedule next scan in 10 seconds
                self.root.after(30000, self.ultra_fast_scan)
            else:
                self.log_message("ARP scan failed")
                # Retry in 10 seconds even on failure
                self.root.after(30000, self.ultra_fast_scan)

        except Exception as e:
            self.log_message(f"Scan failed: {e}")


    def parse_arp_output(self, arp_output):
        """Parse ARP table output to extract devices"""
        devices_dict = {}

        try:
            lines = arp_output.split('\n')
            for line in lines:
                # Look for IP addresses in ARP output
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    ip = ip_match.group(1)

                    # Skip multicast addresses (224.0.0.0 - 239.255.255.255)
                    ip_parts = ip.split('.')
                    if len(ip_parts) == 4 and 224 <= int(ip_parts[0]) <= 239:
                        continue

                    # Skip network infrastructure addresses
                    if self.is_network_infrastructure(ip):
                        continue

                    # Try to get MAC with improved detection
                    mac = self.extract_mac_address(line)
                    if not mac:
                        mac = "Unknown"

                    # Deduplicate by IP, preferring entries with valid MAC
                    if ip not in devices_dict or (mac != "Unknown" and devices_dict[ip]['mac'] == "Unknown"):
                        custom_name = f"Device-{ip.split('.')[-1]}"
                        notify = True
                        if mac != "Unknown" and mac in self.saved_devices:
                            custom_name = self.saved_devices[mac].get('custom_name', custom_name)
                            notify = self.saved_devices[mac].get('notify', True)
                        devices_dict[ip] = {
                            'ip': ip,
                            'mac': mac,
                            'custom_name': custom_name,
                            'notify': notify
                        }
                        # Update saved_devices
                        if mac != "Unknown":
                            self.saved_devices[mac] = {'custom_name': custom_name, 'notify': notify}

        except Exception as e:
            self.log_message(f"Error parsing ARP output: {e}")

        return list(devices_dict.values())

    def update_display(self):
        """Update the device display"""
        # Clear existing items
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)

        # Add devices to treeview
        for device in self.device_list:
            notify_symbol = "☑" if device['notify'] else "☐"
            self.device_tree.insert("", tk.END, values=(
                device['ip'],
                device['custom_name'],
                device['mac'].upper(),
                notify_symbol
            ))

        # Update connected devices count
        self.list_frame.configure(text=f"{len(self.device_list)} Connected Devices")
        # Update tray icon tooltip
        self.update_tray_tooltip()


    def edit_custom_name(self, event):
        """Edit the custom name on double-click"""
        item = self.device_tree.identify_row(event.y)
        column = self.device_tree.identify_column(event.x)

        if item and column == '#2':  # Custom Name column
            values = self.device_tree.item(item, 'values')
            current_name = values[1]
            ip = values[0]
            mac = values[2]

            # Use simpledialog to get new name
            from tkinter import simpledialog
            new_name = simpledialog.askstring("Edit Custom Name", "Enter new custom name:", initialvalue=current_name)

            if new_name is not None:
                # Update the device list
                for device in self.device_list:
                    if device['ip'] == ip:
                        device['custom_name'] = new_name
                        break
                # Update saved data
                if mac != "Unknown":
                    if mac in self.saved_devices:
                        self.saved_devices[mac]['custom_name'] = new_name
                    else:
                        self.saved_devices[mac] = {'custom_name': new_name, 'notify': True}
                self.save_devices()
                self.update_display()
            return "break"
        return None

    def toggle_notify(self, event):
        """Toggle the notify checkbox on click"""
        item = self.device_tree.identify_row(event.y)
        column = self.device_tree.identify_column(event.x)

        if item and column == '#4':  # Notify column
            values = self.device_tree.item(item, 'values')
            ip = values[0]
            mac = values[2]

            # Toggle the notify flag
            notify_value = False
            for device in self.device_list:
                if device['ip'] == ip:
                    device['notify'] = not device['notify']
                    notify_value = device['notify']
                    break
            # Update saved data
            if mac != "Unknown":
                if mac in self.saved_devices:
                    self.saved_devices[mac]['notify'] = notify_value
                else:
                    self.saved_devices[mac] = {'custom_name': f"Device-{ip.split('.')[-1]}", 'notify': notify_value}
            self.save_devices()
            self.update_display()
            return "break"
        return None

    def create_tray_icon(self):
        """Create system tray icon using win32"""
        try:
            self.log_message("Creating tray icon with win32...")
            self.create_tray_with_win32()
            self.log_message("Tray icon created")
        except Exception as e:
            self.log_message(f"Failed to create tray icon: {e}")

    def create_tray_with_win32(self):
        """Create tray icon using win32api"""
        # Create window class
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.tray_wnd_proc
        wc.lpszClassName = "KonekTrayClass"
        wc.hInstance = win32api.GetModuleHandle(None)
        self.class_atom = win32gui.RegisterClass(wc)

        # Create hidden window
        self.hwnd = win32gui.CreateWindow(self.class_atom, "KonekTray", 0, 0, 0, 0, 0, 0, 0, wc.hInstance, None)

        # Load icon
        try:
            icon_path = resource_path("konek.ico")
            self.icon_handle = win32gui.LoadImage(0, icon_path, win32con.IMAGE_ICON, 16, 16, win32con.LR_LOADFROMFILE | win32con.LR_LOADTRANSPARENT | win32con.LR_SHARED)
            self.log_message("Tray icon loaded from konek.ico")
        except Exception as e:
            self.icon_handle = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            self.log_message(f"Failed to load konek.ico: {e}, using default icon")

        # Add to tray
        self.nid = (self.hwnd, 0, win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP, win32con.WM_USER + 20, self.icon_handle, "Konek")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self.nid)

        # Start message loop in separate thread
        import threading
        threading.Thread(target=self.tray_message_loop, daemon=True).start()

    def update_tray_tooltip(self):
        """Update the tray icon tooltip"""
        try:
            self.nid = (self.hwnd, 0, win32gui.NIF_TIP, 0, 0, f"Konek - {len(self.device_list)} Devices")
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self.nid)
            self.log_message(f"Tray tooltip updated to: Konek - {len(self.device_list)} Devices")
        except Exception as e:
            self.log_message(f"Failed to update tray tooltip: {e}")

    def tray_wnd_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure for tray icon"""
        if msg == win32con.WM_USER + 20:
            if lparam == win32con.WM_LBUTTONDBLCLK:
                self.tray_queue.put('show')
            elif lparam == win32con.WM_RBUTTONUP:
                self.tray_queue.put('menu')
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def tray_message_loop(self):
        """Message loop for tray icon"""
        win32gui.PumpMessages()

    def check_tray_queue(self):
        """Check the tray queue for actions from tray thread"""
        try:
            while True:
                action = self.tray_queue.get_nowait()
                if action == 'show':
                    self.log_message("Tray icon double-clicked")
                    self.show_window()
                elif action == 'menu':
                    self.show_tray_menu()
        except queue.Empty:
            pass
        self.root.after(100, self.check_tray_queue)

    def show_tray_menu(self):
        """Show tray menu on right-click"""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1, "Show")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 2, "Quit")
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(menu, win32con.TPM_RETURNCMD | win32con.TPM_NONOTIFY, pos[0], pos[1], 0, self.hwnd, None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        if cmd == 1:
            self.root.after(0, self.show_window)
        elif cmd == 2:
            self.root.after(0, self.quit_app)
        win32gui.DestroyMenu(menu)

    def show_window(self):
        """Show the main window"""
        self.root.deiconify()
        self.root.state('normal')
        self.root.lift()
        self.root.focus_force()
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))


    def quit_app(self):
        """Quit the application"""
        try:
            win32api.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)
            import time
            time.sleep(0.1)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self.nid)
        except:
            pass
        self.root.quit()

    def on_closing(self):
        """Handle window close event - minimize to tray"""
        self.root.withdraw()

    def run(self):
        """Start the application"""
        self.log_message("Ultra-Fast Network Monitor started")
        self.root.mainloop()

def main():
    """Main application entry point"""
    app = UltraFastMonitor()
    app.run()

if __name__ == "__main__":
    main()