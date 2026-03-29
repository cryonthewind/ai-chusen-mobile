# Phone Sync Automation (AI Chusen)

## 1. Problem Statement
Managing a large number of physical phones for automated social media care, account nurturing, or interaction is manually intensive and prone to detection. Users need a system that allows them to control multiple devices simultaneously, synchronize actions, and perform automated sequences while maintaining stealth (IP rotation, User-Agent spoofing).

## 2. Goals
- **Multi-Device Control:** Mirror and control multiple Android phones from a central PC interface.
- **Synchronization:** Perform actions (taps, swipes, typing) on a master device and have them mirrored to all other connected devices simultaneously.
- **Task Automation:** Execute a series of pre-defined steps (automated "cs") on all devices.
- **Stealth and Network Management:**
  - Toggle Airplane Mode to rotate mobile IP addresses.
  - Ability to rotate User-Agent (where applicable) to avoid anti-bot detection.

## 3. Non-Goals
- Support for iOS devices (initially focus on Android due to ADB ease of use).
- Advanced image recognition for automation (initially focus on coordinate-based or element-based automation).
- Building our own screen-mirroring technology (will leverage existing tools like `scrcpy`).

## 4. User Stories
- **As a Marketer**, I want to link 10 phones to my PC so I can see their screens in one view.
- **As a Social Media Manager**, I want to perform a set of interaction steps on one phone and have all other phones do the same thing instantly.
- **As an Automation Engineer**, I want to set up an automated script that runs every morning to like, comment, or scroll on specific profiles.
- **As a Stealth Operator**, I want the system to automatically toggle Airplane Mode between tasks so each action comes from a fresh IP.

## 5. Success Criteria
- [ ] Successfully mirror 3+ phones with minimal lag.
- [ ] Tap on the master phone is mirrored to all slave phones with <100ms latency.
- [ ] Automated scripts can be loaded and executed sequentially.
- [ ] Airplane Mode toggle successfully changes the public IP on the device.

## 6. Constraints
- Devices must be connected via ADB (USB or Wifi).
- Control of system settings like Airplane Mode may vary across Android versions and may require specific permissions or root on some devices.

## 7. Open Questions
- Should the "master" phone be one of the physical devices, or a dedicated "virtual" control panel on the PC?
- For User-Agent rotation, is the "cs" happening in a standard browser or within a native app?
- How many devices do we need to support simultaneously for the initial version?
