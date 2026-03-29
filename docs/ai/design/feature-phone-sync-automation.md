# Phone Sync Automation (AI Chusen) Design

## 1. System Architecture
The system will consist of a central PC application (the "Controller") that interacts with multiple physical Android devices via **ADB (Android Debug Bridge)** and **scrcpy**.

### Components:
- **Controller Interface:** A dashboard to view mirrored screens and trigger automated sequences.
- **ADB Bridge:** Manages device connections (USB/Wifi) and sends commands.
- **Event Relay:** Capture mouse/keyboard events from the "master" view and broadcast them to all "slave" devices.
- **Automation Engine:** Reads a task list (YAML/JSON) and executes ADB shell commands for each device.
- **Network Proxy/Controller:** Handles Airplane mode toggle and potentially routes traffic through a specific User-Agent.

## 2. Technical Stack
- **Language:** Node.js (with `electron` for GUI if needed) or Python.
- **Device Interaction:** `adb` (via shell or `node-adb-api` / `pure-python-adb`).
- **Screen Mirroring:** `scrcpy` binary integration.
- **Automation Framework:** `uiautomator2` (Python) or a custom ADB-based input relay.

## 3. Data Flow
1. **Device Discovery:** Controller scans for devices via `adb devices`.
2. **Mirroring:** Controller launches an `scrcpy` instance per device in a tiled window layout.
3. **Action Syncing:**
   - User clicks on Device A (Master).
   - Controller captures coordinates `(x, y)`.
   - Controller sends `adb -s <serial> shell input tap x y` to all other devices (Slaves).
4. **Automation Execution:**
   - Script starts: `step 1: tap(200, 300)`.
   - Controller loops through connected devices and executes the command on each.

## 4. Key Implementation Details
### Airplane Mode Toggle (IP Rotation)
```bash
# Enable Airplane Mode
adb shell settings put global airplane_mode_on 1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true

# Wait 5-10s for IP to reset

# Disable Airplane Mode
adb shell settings put global airplane_mode_on 0
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false
```

### User-Agent Spoofing
- **If Web-based:** Launch Chrome with `--user-agent` flag via `adb shell am start -n com.android.chrome/com.google.android.apps.chrome.Main -d "url" --es "com.android.browser.headers" "User-Agent: YOUR_UA"`.
- **If App-based:** May require a system-wide proxy (like MITMProxy) configured on the device to inject/rewrite headers.

## 5. Security & Performance Considerations
- **USB Bandwidth:** Controlling too many devices via one USB hub can lead to lag.
- **ADB Reliability:** ADB connections can sometimes drop. Reconnection logic is essential.
- **Anti-Bot:** Randomize tap coordinates slightly (e.g., `x + random(-5, 5)`) to avoid perfectly identical patterns across 10 devices.
