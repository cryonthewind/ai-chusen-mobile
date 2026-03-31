import os
import streamlit as st
import pandas as pd
import time
import subprocess
import threading
import random
import streamlit.components.v1 as components

# --- FIX PATHS FOR MAC PRODUCTION ---
EXT_PATHS = [
    "/Users/toandz/Library/Android/sdk/platform-tools",
    "/usr/local/bin",
    "/opt/homebrew/bin"
]
for p in EXT_PATHS:
    if p not in os.environ["PATH"]:
        os.environ["PATH"] = f"{p}:{os.environ['PATH']}"

from src.core.robot import AdbRobot
from src.workflow.lottery_workflow import run_lottery_workflow
from src.utils.config import Config

# --- CONFIG ---
st.set_page_config(page_title="AI CHUSEN | MATRIX OPS", layout="wide", page_icon="🧬", initial_sidebar_state="collapsed")

# --- FULL MATRIX CYBERPUNK CSS ---
MATRIX_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    :root {
        --matrix-green: #00ff41;
        --matrix-faded: rgba(0, 255, 65, 0.15);
        --matrix-bg: #010801;
        --card-dark: rgba(13, 13, 13, 0.98);
    }

    body, html, .stApp { 
        background-color: var(--matrix-bg) !important; 
        color: var(--matrix-green) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    header { visibility: hidden; }
    .block-container { padding: 1.5rem 3rem !important; }

    /* Matrix Glow Panel */
    .matrix-panel {
        background: var(--card-dark);
        border: 1.5px solid var(--matrix-green);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 0 15px var(--matrix-faded);
    }
    .active-glow { box-shadow: 0 0 35px var(--matrix-green); border-color: #fff; }

    .kpi-label { font-size: 0.6rem; color: #fff; text-transform: uppercase; letter-spacing: 0.2em; opacity: 0.6; margin-bottom: 5px; }
    .kpi-value { font-size: 2.22rem; font-weight: 800; color: var(--matrix-green); text-shadow: 0 0 10px var(--matrix-green); line-height: 1; }

    /* Log Viewport */
    .log-viewport {
        background: #000;
        border: 1px solid rgba(0, 255, 65, 0.3);
        border-radius: 8px;
        padding: 12px;
        height: 180px;
        overflow-y: auto;
        color: #00ff41;
        font-size: 11px;
        margin-bottom: 12px;
    }
    .log-line { border-bottom: 1px solid rgba(0,255,65,0.05); padding: 4px 0; }

    /* Matrix Interactive Buttons */
    .stButton>button {
        background: transparent !important;
        color: var(--matrix-green) !important;
        border: 1.5px solid var(--matrix-green) !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        font-size: 10px !important;
        transition: all 0.2s !important;
    }
    .stButton>button:hover {
        background: var(--matrix-green) !important;
        color: #000 !important;
        box-shadow: 0 0 20px var(--matrix-green) !important;
    }

    /* Table Specialist Mode */
    .m-table-wrap { background: #000; border: 1.5px solid var(--matrix-green); border-radius: 12px; overflow: hidden; }
    .m-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
    .m-table th { background: #002200; color: #fff; padding: 15px; text-align: left; border-bottom: 2px solid var(--matrix-green); }
    .m-table td { padding: 12px 15px; border-bottom: 1px solid rgba(0, 255, 65, 0.1); color: #00ff41; }
    
    .stDivider { border-color: rgba(0, 255, 65, 0.2) !important; }
</style>
"""

st.markdown(MATRIX_STYLE, unsafe_allow_html=True)

# --- GLOBAL STATE ---
class GlobalRobotStatus:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalRobotStatus, cls).__new__(cls)
            cls._instance.worker_status = {}
            cls._instance.device_logs = {}
            cls._instance.stop_flags = {}
            cls._instance.scrcpy_processes = {} # Dùng để quản lý các cửa sổ VIEW
            cls._instance.account_counts = {}   # Theo dõi 10 lần thì reset IP
        return cls._instance
    def add_log(self, serial, message):
        if serial not in self.device_logs: self.device_logs[serial] = []
        ts = time.strftime("%H:%M:%S")
        self.device_logs[serial].append(f'<div class="log-line"><span style="opacity:0.4">[{ts}]</span> {message}</div>')
        if len(self.device_logs[serial]) > 30: self.device_logs[serial].pop(0)

if 'robot_state' not in st.session_state: st.session_state.robot_state = GlobalRobotStatus()
robot_state = st.session_state.robot_state

def get_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode().splitlines()
        return [l.split()[0] for l in output[1:] if "device" in l and not "devices" in l]
    except: return []

def worker_thread(serial, file_path):
    robot_state.worker_status[serial] = "RUNNING"; robot_state.stop_flags[serial] = False
    try:
        robot = AdbRobot(serial)
        while not robot_state.stop_flags.get(serial, False):
            df = pd.read_csv(file_path)
            mask = ((df['Device_Serial'] == serial) | (df['Device_Serial'].isna()) | (df['Device_Serial'] == '')) & (df['Status'] == 'ready')
            if not df[mask].any().any():
                robot_state.add_log(serial, "✅ QUEUE_CLEARED"); robot_state.worker_status[serial] = "IDLE"; break
            idx = df[mask].index[0]; acc = df.iloc[idx].to_dict()
            df.at[idx, 'Status'] = 'Running'; df.at[idx, 'Device_Serial'] = serial; df.to_csv(file_path, index=False)
            
            # Lambda check stop flag
            def stop_check(): return robot_state.stop_flags.get(serial, False)
            res = run_lottery_workflow(serial, acc, log_callback=robot_state.add_log, stop_check=stop_check)
            
            # Finish update
            df = pd.read_csv(file_path)
            new_status = 'ready' if res.get('status') == 'STOPPED' else ('Completed' if res.get('status') in ["SUCCESS", "SKIP"] else 'Error')
            df.at[idx, 'Status'] = new_status
            df.to_csv(file_path, index=False)

            if res.get('status') == 'STOPPED': break

            # --- AUTO RESET IP LOGIC (Sau 10 accounts) ---
            if res.get('status') in ["SUCCESS", "SKIP"]:
                current_count = robot_state.account_counts.get(serial, 0) + 1
                robot_state.account_counts[serial] = current_count
                robot_state.add_log(serial, f"📊 Progress: {current_count}/10 accounts.")
                
                if current_count >= 10:
                    robot_state.add_log(serial, "🔄 Auto Trigger: Resetting IP after 10 accounts...")
                    robot.toggle_airplane_mode(log_callback=robot_state.add_log)
                    robot_state.account_counts[serial] = 0 # Reset counter

            # Interruptible Sleep (15-30s)
            wait_time = random.randint(15, 30)
            for _ in range(wait_time):
                if stop_check(): break
                time.sleep(1)
    except Exception as e:
        robot_state.add_log(serial, f"❌ CRITICAL_ERROR: {e}"); robot_state.worker_status[serial] = "CRASHED"
    finally:
        robot_state.stop_flags[serial] = False
        robot_state.worker_status[serial] = "IDLE"

# --- HEADER & KPI RENDERING ---
st.markdown('<div style="text-align:center; padding-bottom:1.5rem"><span style="letter-spacing:1.2em; border:1.5px solid var(--matrix-green); padding:8px 25px; font-weight:700; box-shadow: 0 0 15px var(--matrix-green); color:var(--matrix-green)">MATRIX MONITORING SYSTEM</span></div>', unsafe_allow_html=True)

accounts_file = "accounts_template.csv"
if os.path.exists(accounts_file):
    df_all = pd.read_csv(accounts_file)
    active = sum(1 for s in robot_state.worker_status.values() if "RUNNING" in str(s))
    
    # KPIs Row
    ks = st.columns(5)
    with ks[0]: st.markdown(f'<div class="matrix-panel"><div class="kpi-label">Queued</div><div class="kpi-value">{len(df_all[df_all["Status"]=="ready"])}</div></div>', unsafe_allow_html=True)
    with ks[1]: st.markdown(f'<div class="matrix-panel"><div class="kpi-label">Active</div><div class="kpi-value">{active}</div></div>', unsafe_allow_html=True)
    with ks[2]: st.markdown(f'<div class="matrix-panel"><div class="kpi-label">Success</div><div class="kpi-value">{len(df_all[df_all["Status"]=="Completed"])}</div></div>', unsafe_allow_html=True)
    with ks[3]: st.markdown(f'<div class="matrix-panel"><div class="kpi-label">Failed</div><div class="kpi-value">{len(df_all[df_all["Status"].isin(["Error", "Redirect"])])}</div></div>', unsafe_allow_html=True)
    with ks[4]: st.markdown(f'<div class="matrix-panel"><div class="kpi-label">Total</div><div class="kpi-value">{len(df_all)}</div></div>', unsafe_allow_html=True)

    st.divider()

    # CORE GRID
    l_col, r_col = st.columns([0.76, 0.24])
    devs = get_devices()
    
    with l_col:
        st.markdown('<p style="font-weight:700; opacity:0.8"># NODE_AGENTS_ONLINE</p>', unsafe_allow_html=True)
        gc = st.columns(2)
        for i, sn in enumerate(devs):
            with gc[i % 2]:
                stt = robot_state.worker_status.get(sn, "IDLE")
                logs = robot_state.device_logs.get(sn, ["Establishing matrix link..."])
                glow = "active-glow" if "RUNNING" in str(stt) else ""
                
                st.markdown(f"""
                <div class="matrix-panel {glow}" style="margin-bottom:1rem">
                    <div style="font-weight:700; margin-bottom:10px">[ {sn} ] <span style="float:right">{stt}</span></div>
                    <div class="log-viewport">{''.join(logs[::-1])}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Device Action Buttons (5 Columns Matrix Layout)
                btn_cols = st.columns(5)
                if btn_cols[0].button("▶ RUN", key=f"r_{sn}", use_container_width=True): 
                    threading.Thread(target=worker_thread, args=(sn, accounts_file), daemon=True).start()
                if btn_cols[1].button("🛑 OFF", key=f"s_{sn}", use_container_width=True): 
                    robot_state.stop_flags[sn] = True
                if btn_cols[2].button("📺 VIEW", key=f"v_{sn}", use_container_width=True): 
                    # Mở và lưu tiến trình scrcpy
                    p = subprocess.Popen(["scrcpy", "-s", sn])
                    robot_state.scrcpy_processes[sn] = p
                if btn_cols[3].button("❌ CLS", key=f"c_{sn}", use_container_width=True): 
                    # Đóng monitor của riêng SN này
                    p = robot_state.scrcpy_processes.get(sn)
                    if p:
                        p.terminate()
                        del robot_state.scrcpy_processes[sn]
                if btn_cols[4].button("✈ IP", key=f"i_{sn}", use_container_width=True): 
                    threading.Thread(target=lambda: AdbRobot(sn).toggle_airplane_mode(log_callback=robot_state.add_log), daemon=True).start()


    with r_col:
        st.markdown('<p style="font-weight:700; opacity:0.8"># GLOBAL_OPS (SYNC)</p>', unsafe_allow_html=True)
        
        # 🎯 THÊM NÚT SCAN DEVICES (NODE DETECTION)
        if st.button("🔭 SCAN FOR NEW NODES", use_container_width=True):
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="matrix-panel" style="font-size:0.7rem">ENCRYPTION: SHIELDED<br>NODE_DETECTION: AUTO<br>IP_RELAY: OPERATIONAL</div>', unsafe_allow_html=True)

    # --- TRANSMISSION FEED (QUEUE CONTROLS) ---
    st.markdown('<p style="font-weight:700; margin-top:2.5rem; opacity:0.8"># TRANSMISSION_QUEUE_FEED_BUFFER</p>', unsafe_allow_html=True)
    
    ctrl_l, ctrl_r = st.columns([0.5, 0.5])
    with ctrl_l:
        if st.button("♻️ RETRY FAILED ACCOUNTS (ERROR/REDIRECT)", use_container_width=True):
            df_all.loc[df_all['Status'].isin(['Error', 'Redirect']), 'Status'] = 'ready'
            df_all.to_csv(accounts_file, index=False); st.rerun()
    with ctrl_r:
        if st.button("⚠️ RESET ALL HUB (RELOAD_FROM_ZERO)", use_container_width=True):
            df_all['Status']='ready'; df_all['Device_Serial']=''; df_all.to_csv(accounts_file, index=False); st.rerun()

    rows = ""
    # Render top 100 accounts in natural order
    for _, row in df_all.head(100).iterrows():
        rows += f"<tr><td>{row['Account_Email']}</td><td style='font-weight:bold'>{row['Status']}</td><td>{row.get('Device_Serial','-')}</td></tr>"
    
    html_out = f"""
    {MATRIX_STYLE}
    <div class="m-table-wrap">
        <table class="m-table">
            <thead><tr><th>SOURCE_EMAIL</th><th>STATUS</th><th>NODE_ID</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
    components.html(html_out, height=450, scrolling=True)

    time.sleep(5); st.rerun()
else:
    st.error("DATABASE_UNREACHABLE")
