import streamlit as st
import pandas as pd
import time
import os
import random
import subprocess
import threading
import logging
from src.core.robot import AdbRobot
from src.workflow.lottery_workflow import run_lottery_workflow

# Cấu hình giao diện Streamlit Premium
st.set_page_config(page_title="AI CHUSEN PRO | Control Center", layout="wide", page_icon="🤖")

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #e2e8f0; }
    .main-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-radius: 16px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 20px; }
    .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
    .log-box { background: #000; color: #00ff00; font-family: 'Courier New', Courier, monospace; font-size: 11px; padding: 10px; border-radius: 8px; height: 250px; overflow-y: auto; border: 1px solid #333; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

class GlobalRobotStatus:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalRobotStatus, cls).__new__(cls)
            cls._instance.worker_status = {}
            cls._instance.device_logs = {}
            cls._instance.stop_flags = {}
        return cls._instance

    def add_log(self, serial, message):
        if serial not in self.device_logs: self.device_logs[serial] = []
        timestamp = time.strftime("%H:%M:%S")
        self.device_logs[serial].append(f"[{timestamp}] {message}")
        if len(self.device_logs[serial]) > 100: self.device_logs[serial].pop(0)

if 'robot_state' not in st.session_state:
    st.session_state.robot_state = GlobalRobotStatus()
robot_state = st.session_state.robot_state

def list_adb_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode()
        lines = output.splitlines()
        return [line.split()[0] for line in lines[1:] if "device" in line and not "devices" in line]
    except:
        return []

def worker_thread(serial, accounts_file):
    """Xử lý song song cho 1 máy."""
    robot_state.worker_status[serial] = "⚡ PROCESSING"
    robot_state.stop_flags[serial] = False
    robot_state.add_log(serial, "Worker Engine Khởi động...")
    
    acc_count = 0 
    try:
        robot = AdbRobot(serial) 
        
        while not robot_state.stop_flags.get(serial, False):
            # 1. Quản lý Đọc/Ghi CSV an toàn
            df = pd.read_csv(accounts_file)
            df['Device_Serial'] = df['Device_Serial'].fillna('')
            target_mask = ((df['Device_Serial'] == serial) | (df['Device_Serial'] == '')) & (df['Status'] == 'ready')
            
            if not df[target_mask].any().any():
                robot_state.add_log(serial, "Hết tài khoản 'ready'. Kết thúc.")
                robot_state.worker_status[serial] = "🏁 FINISHED"
                break
                
            idx = df[target_mask].index[0]
            row = df.iloc[idx].to_dict()
            acc_email = row['Account_Email']
            
            # Khóa account
            df.at[idx, 'Device_Serial'] = serial
            df.at[idx, 'Status'] = 'Running'
            df.to_csv(accounts_file, index=False)
            
            robot_state.add_log(serial, f"🚀 Đang xử lý: {acc_email}")
            
            # --- CHẠY LOTTERY WORKFLOW (ARCHITECTURE V3) ---
            res = run_lottery_workflow(serial, row, log_callback=robot_state.add_log)
            
            # Cập nhật kết quả cuối cùng
            df = pd.read_csv(accounts_file)
            df.at[idx, 'Status'] = 'Completed' if res['status'] == "SUCCESS" or res['status'] == "SKIP" else 'Error'
            df.to_csv(accounts_file, index=False)
            
            # Đếm số lượng để reset IP
            acc_count += 1
            if acc_count >= 10:
                robot_state.add_log(serial, "✈️ Đã làm xong 10 accounts, đang tự động đổi IP...")
                robot.toggle_airplane_mode()
                acc_count = 0
            
            # Nghỉ ngơi trùm chống Bot
            wait = random.randint(15, 30)
            robot_state.add_log(serial, f"Bot Cooldown: {wait}s...")
            time.sleep(wait)
            
    except Exception as e:
        robot_state.add_log(serial, f"💥 Lỗi Worker: {e}")
        robot_state.worker_status[serial] = "❌ ERROR"
    finally:
        # Quan trọng: Reset trạng thái để có thể bấm nút Chạy lại
        if robot_state.stop_flags.get(serial):
            robot_state.add_log(serial, "🛑 Đã Dừng worker theo yêu cầu.")
            robot_state.worker_status[serial] = "IDLE (Stopped)"
        robot_state.stop_flags[serial] = False # Clear flag cho lần sau

# UI HEADER
st.title("🛡️ AI CHUSEN CONTROL CENTER | V3 ARCHITECTURE")
accounts_file = "accounts_template.csv"

if os.path.exists(accounts_file):
    df_all = pd.read_csv(accounts_file)
    
    # METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng tài khoản", len(df_all))
    m2.metric("Sẵn sàng quét", len(df_all[df_all['Status'] == 'ready']))
    m3.metric("Hoàn tất ✅", len(df_all[df_all['Status'] == 'Completed']))
    m4.metric("Lỗi cần check ❌", len(df_all[df_all['Status'].isin(['Error', 'Redirect'])]))

    st.sidebar.title("🎮 Dashboard Settings")
    if st.sidebar.button("🔍 SCAN DEVICES"):
        st.session_state.devices_list = list_adb_devices()
        st.rerun()

    devices = st.session_state.get('devices_list', [])

    if devices:
        st.subheader(f"📱 Hoạt động (Online: {len(devices)})")
        cols = st.columns(3)
        for i, serial in enumerate(devices):
            with cols[i % 3]:
                status = robot_state.worker_status.get(serial, "IDLE")
                logs = robot_state.device_logs.get(serial, ["Đang đợi lệnh quét..."])
                
                st.markdown(f"""<div class="main-card">
                    <div style="display:flex; justify-content:space-between; align-items:center">
                        <h4 style="margin:0">Device: {serial}</h4>
                        <span class="status-badge" style="background:{'#10b981' if 'PROCESSING' in status else '#64748b'}">{status}</span>
                    </div>
                    <hr style="margin:10px 0; border:0; border-top:1px solid #333">
                    <div class="log-box">{"<br>".join(logs[::-1])}</div>
                </div>""", unsafe_allow_html=True)
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    is_running = "PROCESSING" in robot_state.worker_status.get(serial, "")
                    if st.button(f"▶️ Chạy", key=f"run_{serial}", disabled=is_running):
                        threading.Thread(target=worker_thread, args=(serial, accounts_file), daemon=True).start()
                with c2:
                    if st.button(f"🛑 Dừng", key=f"stop_{serial}"):
                        robot_state.stop_flags[serial] = True
                with c3:
                    if st.button(f"📺 Xem", key=f"view_{serial}"):
                        subprocess.Popen(["scrcpy", "-s", serial])
                with c4:
                    if st.button(f"✈️ IP", key=f"ip_{serial}"):
                        # Reset IP thủ công ngay lập tức
                        threading.Thread(target=lambda: AdbRobot(serial).toggle_airplane_mode(), daemon=True).start()
                        robot_state.add_log(serial, "✈️ Yêu cầu Reset IP thủ công...")
    
    st.divider()
    with st.expander("📊 Account Database Management"):
        st.dataframe(df_all, use_container_width=True)
        colL1, colL2, colL3 = st.columns(3)
        if colL1.button("🔄 Reset All to Ready"):
            df_all['Status'] = 'ready'; df_all['Device_Serial'] = ''; df_all.to_csv(accounts_file, index=False); st.rerun()
        if colL2.button("🔄 Retry Errors"):
            df_all.loc[df_all['Status'].isin(['Error', 'Running']), 'Status'] = 'ready'; df_all.to_csv(accounts_file, index=False); st.rerun()

else:
    st.error("Missing accounts_template.csv")

time.sleep(3)
st.rerun()
