import streamlit as st
import pandas as pd
import time
import os
import random
import subprocess
import threading
from adb_helper import list_devices, SmartAdbDevice
from main import process_account_smart

# Cấu hình giao diện Streamlit Premium
st.set_page_config(page_title="AI CHUSEN PRO | Control Center", layout="wide", page_icon="🤖")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #e2e8f0; }
    .main-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border-radius: 16px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 20px; }
    .log-box { background: #000; color: #00ff00; font-family: 'Courier New', Courier, monospace; font-size: 11px; padding: 10px; border-radius: 8px; height: 150px; overflow-y: auto; border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

class GlobalRobotStatus:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalRobotStatus, cls).__new__(cls)
            cls._instance.worker_status = {}
            cls._instance.account_counters = {}
            cls._instance.stop_flags = {}
            cls._instance.device_logs = {} # {serial: []}
            cls._instance.global_logs = []
        return cls._instance

    def add_log(self, serial, message):
        if serial not in self.device_logs: self.device_logs[serial] = []
        timestamp = time.strftime("%H:%M:%S")
        msg = f"[{timestamp}] {message}"
        self.device_logs[serial].append(msg)
        if len(self.device_logs[serial]) > 20: self.device_logs[serial].pop(0)

if 'robot_state' not in st.session_state:
    st.session_state.robot_state = GlobalRobotStatus()
robot_state = st.session_state.robot_state

def run_worker_parallel(serial, accounts_file):
    robot_state.worker_status[serial] = "⚡ PROCESSING"
    robot_state.account_counters[serial] = 0
    robot_state.stop_flags[serial] = False
    
    robot_state.add_log(serial, "Kết nối thiết bị...")
    try:
        device = SmartAdbDevice(serial)
    except Exception as e:
        robot_state.add_log(serial, f"Lỗi kết nối: {e}")
        return

    while not robot_state.stop_flags.get(serial, False):
        try:
            df = pd.read_csv(accounts_file)
            # Lọc theo serial hoặc serial trống và trạng thái ready
            # Dùng .fillna('') để xử lý NaN khi so sánh
            df['Device_Serial'] = df['Device_Serial'].fillna('')
            pending = df[((df['Device_Serial'] == serial) | (df['Device_Serial'] == '')) & (df['Status'] == 'ready')]
            
            if pending.empty:
                robot_state.add_log(serial, "Không còn tài khoản 'ready' cho máy này.")
                robot_state.worker_status[serial] = "🏁 COMPLETED"
                break
                
            index = pending.index[0]
            row = pending.iloc[0].to_dict()
            target_account = row['Account_Email']
            
            # Gắn serial vào account ngay khi lấy để đánh dấu đang xử lý
            df.at[index, 'Device_Serial'] = serial
            df.at[index, 'Status'] = 'Running'
            df.to_csv(accounts_file, index=False)
            
            robot_state.add_log(serial, f"Bắt đầu: {target_account}")
            
            # --- CHẠY AUTOMATION ---
            robot_state.add_log(serial, "Đang mở Chrome ẩn danh...")
            success = process_account_smart(device, row)
            
            # --- CẬP NHẬT KẾ QUẢ ---
            df = pd.read_csv(accounts_file)
            df.at[index, 'Status'] = 'Completed' if success else 'Error'
            df.to_csv(accounts_file, index=False)
            
            robot_state.add_log(serial, f"Kết quả: {'Thành công' if success else 'Thất bại'}")
            robot_state.account_counters[serial] += 1
            device.close_chrome()
            
            # Nghỉ ngơi
            wait = random.randint(3, 10)
            robot_state.add_log(serial, f"Nghỉ ngơi {wait} giây...")
            time.sleep(wait)
            
        except Exception as e:
            robot_state.add_log(serial, f"Lỗi hệ thống: {e}")
            break

# MAIN INTERFACE
st.title("🛡️ AI CHUSEN CONTROL CENTER")
accounts_file = "accounts_template.csv"

if os.path.exists(accounts_file):
    df_all = pd.read_csv(accounts_file)
    
    # METRICS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng tài khoản", len(df_all))
    m2.metric("Sẵn sàng", len(df_all[df_all['Status'] == 'ready']))
    m3.metric("Thành công ✅", len(df_all[df_all['Status'] == 'Completed']))
    m4.metric("Lỗi / Redirect ❌", len(df_all[df_all['Status'].isin(['Error', 'Redirect'])]))

    st.sidebar.title("🛠️ Settings")
    if st.sidebar.button("🔍 QUÉT THIẾT BỊ"):
        st.session_state.devices_list = list_devices()
        st.rerun()

    devices = st.session_state.get('devices_list', [])

    if devices:
        st.subheader("📱 Thiết bị đang vận hành")
        cols = st.columns(3)
        for i, serial in enumerate(devices):
            with cols[i % 3]:
                status = robot_state.worker_status.get(serial, "IDLE")
                logs = robot_state.device_logs.get(serial, ["Đang chờ lệnh..."])
                
                st.markdown(f"""<div class="main-card">
                    <h4>Device: {serial}</h4>
                    <p style="color:#10b981"><b>{status}</b></p>
                    <div class="log-box">{"<br>".join(logs)}</div>
                </div>""", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    is_running = robot_state.worker_status.get(serial, "").startswith("⚡")
                    if st.button(f"▶️ Start", key=f"s_{serial}", disabled=is_running):
                        threading.Thread(target=run_worker_parallel, args=(serial, accounts_file), daemon=True).start()
                with c2:
                    if st.button(f"🛑 Stop", key=f"t_{serial}"):
                        robot_state.stop_flags[serial] = True
                with c3:
                    if st.button(f"📺 Mirror", key=f"m_{serial}"):
                        subprocess.Popen(["scrcpy", "-s", serial])
    
    st.divider()
    with st.expander("📊 DANH SÁCH CHI TIẾT"):
        st.dataframe(df_all, width="stretch")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reset Toàn Bộ (Về Ready)"):
                df_all['Status'] = 'ready'
                df_all.to_csv(accounts_file, index=False)
                st.rerun()
        with col2:
            if st.button("🔄 Thử lại các tài khoản Lỗi / Đang chạy"):
                df_all.loc[df_all['Status'].isin(['Error', 'Running']), 'Status'] = 'ready'
                df_all.to_csv(accounts_file, index=False)
                st.rerun()
else:
    st.error("Không tìm thấy file accounts_template.csv")

# Tự động refresh UI thường xuyên để cập nhật log và trạng thái
# Rerun mỗi 2 giây để đảm bảo UI không bị treo
time.sleep(2)
st.rerun()
