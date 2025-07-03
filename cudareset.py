from PySide6 import QtWidgets, QtCore
import ctypes, subprocess, sys

# Optional imports for extended reset methods
try:
    import pycuda.driver as cuda
except ImportError:
    cuda = None

try:
    from numba import cuda as numba_cuda
except ImportError:
    numba_cuda = None

try:
    from pynvraw import NvRaw
except ImportError:
    NvRaw = None

try:
    import win32api, win32con
except ImportError:
    win32api = None
    win32con = None

class Worker(QtCore.QThread):
    log = QtCore.Signal(str)
    finished = QtCore.Signal()

    def run(self):
        methods = [
            ("CUDA Runtime Reset", self.reset_cuda_runtime),
            ("PyCUDA Context Reset", self.reset_pycuda),
            ("Numba Context Reset", self.reset_numba),
            ("NVAPI GPU Reset", self.reset_nvapi),
            ("Win Key Driver Reset", self.reset_winkey),
            ("DevCon GPU Toggle", self.reset_devcon),
        ]
        for name, func in methods:
            self.log.emit(f"Starting {name}...")
            try:
                func()
                self.log.emit(f"{name} succeeded.")
            except Exception as e:
                self.log.emit(f"{name} failed: {e}")
        self.log.emit("All methods attempted.")
        self.finished.emit()

    def reset_cuda_runtime(self):
        dll_names = ["cudart64_125.dll", "cudart64_120.dll", "cudart64_110.dll"]
        for dll in dll_names:
            try:
                cudart = ctypes.CDLL(dll)
                ret = cudart.cudaDeviceReset()
                if ret == 0:
                    self.log.emit(f"cudaDeviceReset returned {ret} using {dll}")
                    return
            except Exception:
                continue
        raise RuntimeError("cudaDeviceReset failed on all tried DLLs")

    def reset_pycuda(self):
        if not cuda:
            raise ImportError("PyCUDA not installed")
        cuda.init()
        dev = cuda.Device(0)
        ctx = dev.make_context()
        ctx.pop()
        ctx.detach()

    def reset_numba(self):
        if not numba_cuda:
            raise ImportError("Numba CUDA not installed")
        numba_cuda.select_device(0)
        numba_cuda.current_context().reset()

    def reset_nvapi(self):
        if not NvRaw:
            raise ImportError("pynvraw not installed")
        nv = NvRaw()
        nv.NvAPI_Initialize()
        handles = nv.NvAPI_EnumPhysicalGPUs()
        if handles:
            status = nv.NvAPI_GPU_Reset(handles[0])
            if status != 0:
                raise RuntimeError(f"NvAPI_GPU_Reset returned status {status}")
        else:
            raise RuntimeError("No GPUs found")

    def reset_winkey(self):
        if not (win32api and win32con):
            raise ImportError("pywin32 not installed")
        # Simulate Win+Ctrl+Shift+B keypress
        for vk in (win32con.VK_LWIN, win32con.VK_CONTROL, win32con.VK_SHIFT, ord('B')):
            win32api.keybd_event(vk, 0, 0, 0)
        for vk in (ord('B'), win32con.VK_SHIFT, win32con.VK_CONTROL, win32con.VK_LWIN):
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def reset_devcon(self):
        gpu_id = r"PCI\\VEN_10DE&DEV_1C8C&SUBSYS_07981028"
        subprocess.run(["devcon", "disable", gpu_id], check=True)
        subprocess.run(["devcon", "enable", gpu_id], check=True)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPU Reset Utility")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #000000; }
            QWidget#container { background-color: #333333; }
            QTabWidget::pane { background-color: #333333; }
            QTabBar::tab { background-color: #333333; color: white; padding: 10px; }
            QTabBar::tab:selected { background-color: #444444; }
            QPushButton { background-color: #00AA00; color: white; border: none; padding: 8px; }
            QPushButton:hover { background-color: #00CC00; }
            QTextEdit { background-color: #222222; color: #DDDDDD; }
        """)

        tabs = QtWidgets.QTabWidget()
        tabs.setObjectName("container")

        reset_tab = QtWidgets.QWidget()
        reset_layout = QtWidgets.QVBoxLayout(reset_tab)
        self.reset_button = QtWidgets.QPushButton("Reset GPU")
        self.reset_button.clicked.connect(self.start_reset)
        reset_layout.addWidget(self.reset_button)
        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        reset_layout.addWidget(self.log_output)
        tabs.addTab(reset_tab, "Reset")

        self.setCentralWidget(tabs)

        self.worker = Worker()
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.reset_finished)

    def start_reset(self):
        self.reset_button.setEnabled(False)
        self.log_output.clear()
        self.worker.start()

    def log(self, message):
        self.log_output.append(message)

    def reset_finished(self):
        self.reset_button.setEnabled(True)
        self.log_output.append("Reset process finished.")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
