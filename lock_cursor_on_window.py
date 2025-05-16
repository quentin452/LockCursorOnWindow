import ctypes
from ctypes import wintypes
import time

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
psapi = ctypes.WinDLL('psapi', use_last_error=True)

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WS_OVERLAPPEDWINDOW = 0x00CF0000
SW_SHOW = 5
COLOR_WINDOW = 5
IDC_ARROW = 32512

ID_EDIT = 101
ID_BUTTON = 102
ID_UNLOCK_BUTTON = 103  

locked_rect = None
hwnd_target = None  

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSEX(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.UINT),
                ('style', wintypes.UINT),
                ('lpfnWndProc', WNDPROC),
                ('cbClsExtra', ctypes.c_int),
                ('cbWndExtra', ctypes.c_int),
                ('hInstance', wintypes.HINSTANCE),
                ('hIcon', wintypes.HICON),
                ('hCursor', wintypes.HANDLE),
                ('hbrBackground', wintypes.HBRUSH),
                ('lpszMenuName', wintypes.LPCWSTR),
                ('lpszClassName', wintypes.LPCWSTR),
                ('hIconSm', wintypes.HICON)]

class MSG(ctypes.Structure):
    _fields_ = [('hwnd', wintypes.HWND),
                ('message', wintypes.UINT),
                ('wParam', wintypes.WPARAM),
                ('lParam', wintypes.LPARAM),
                ('time', wintypes.DWORD),
                ('pt_x', ctypes.c_long),
                ('pt_y', ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long),
                ('top', ctypes.c_long),
                ('right', ctypes.c_long),
                ('bottom', ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD),
    ]

user32.DefWindowProcW.restype = ctypes.c_long
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

EnumWindows = user32.EnumWindows
EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
EnumWindows.restype = wintypes.BOOL

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GetWindowThreadProcessId.restype = wintypes.DWORD

OpenProcess = kernel32.OpenProcess
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
OpenProcess.restype = wintypes.HANDLE

GetModuleBaseNameW = psapi.GetModuleBaseNameW
GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
GetModuleBaseNameW.restype = wintypes.DWORD

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

GetWindowRect = user32.GetWindowRect
GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
GetWindowRect.restype = wintypes.BOOL

ClipCursor = user32.ClipCursor
ClipCursor.argtypes = [ctypes.POINTER(RECT)]
ClipCursor.restype = wintypes.BOOL

GetDlgItem = user32.GetDlgItem
GetDlgItem.argtypes = [wintypes.HWND, wintypes.INT]
GetDlgItem.restype = wintypes.HWND

GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextLengthW.argtypes = [wintypes.HWND]
GetWindowTextLengthW.restype = ctypes.c_int

GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int

SendMessageW = user32.SendMessageW
SendMessageW.restype = ctypes.c_long 
SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

MonitorFromWindow = user32.MonitorFromWindow
MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
MonitorFromWindow.restype = wintypes.HMONITOR

GetMonitorInfo = user32.GetMonitorInfoW
GetMonitorInfo.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
GetMonitorInfo.restype = wintypes.BOOL

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND
GetForegroundWindow.argtypes = []

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010

MONITOR_DEFAULTTONEAREST = 2

def find_hwnd_by_process_name(proc_name_target):
    proc_name_target = proc_name_target.lower()
    hwnd_found = wintypes.HWND()

    def enum_proc(hwnd, lParam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid.value)
        if process_handle:
            buf = ctypes.create_unicode_buffer(260)
            if GetModuleBaseNameW(process_handle, None, buf, 260) > 0:
                if buf.value.lower() == proc_name_target and user32.IsWindowVisible(hwnd):
                    hwnd_found.value = hwnd
                    CloseHandle(process_handle)
                    return False  
            CloseHandle(process_handle)
        return True 

    EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_proc), 0)
    return hwnd_found.value

def clip_cursor_to_window(hwnd_target):
    global locked_rect
    rect = RECT()
    if not GetWindowRect(hwnd_target, ctypes.byref(rect)):
        print("Erreur GetWindowRect")
        return False

    hMonitor = MonitorFromWindow(hwnd_target, MONITOR_DEFAULTTONEAREST)
    if not hMonitor:
        print("Erreur MonitorFromWindow")
        return False

    monitor_info = MONITORINFO()
    monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
    if not GetMonitorInfo(hMonitor, ctypes.byref(monitor_info)):
        print("Erreur GetMonitorInfo")
        return False

    if rect.left < monitor_info.rcMonitor.left:
        rect.left = monitor_info.rcMonitor.left - 1
    if rect.top < monitor_info.rcMonitor.top:
        rect.top = monitor_info.rcMonitor.top - 1
    if rect.right > monitor_info.rcMonitor.right:
        rect.right = monitor_info.rcMonitor.right - 1
    if rect.bottom > monitor_info.rcMonitor.bottom:
        rect.bottom = monitor_info.rcMonitor.bottom - 1

    locked_rect = rect

    if not ClipCursor(ctypes.byref(rect)):
        print("Erreur ClipCursor")
        return False

    print(f"Curseur verrouillé dans la fenêtre, borné à l'écran")
    return True

@WNDPROC
def WndProc(hwnd, msg, wparam, lparam):
    global hwnd_target, locked_rect
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    elif msg == WM_COMMAND:
        ctrl_id = wparam & 0xFFFF
        if ctrl_id == ID_BUTTON:
            hEdit = GetDlgItem(hwnd, ID_EDIT)
            length = GetWindowTextLengthW(hEdit)
            buffer = ctypes.create_unicode_buffer(length + 1)
            GetWindowTextW(hEdit, buffer, length + 1)
            proc_name = buffer.value.strip()
            if proc_name:
                hwnd_found = find_hwnd_by_process_name(proc_name)
                if hwnd_found:
                    hwnd_target = hwnd_found
                    if not clip_cursor_to_window(hwnd_target):
                        print("Erreur lors du verrouillage du curseur")
                else:
                    print(f"Fenêtre pour '{proc_name}' non trouvée")
                    hwnd_target = None
                    locked_rect = None
            else:
                print("Nom de processus vide")
        elif ctrl_id == ID_UNLOCK_BUTTON:
            ClipCursor(None)
            hwnd_target = None
            locked_rect = None
            print("Curseur déverrouillé.")
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

def main():
    hInstance = kernel32.GetModuleHandleW(None)
    className = "MyPythonWindowClass"

    wndClass = WNDCLASSEX()
    wndClass.cbSize = ctypes.sizeof(WNDCLASSEX)
    wndClass.style = 0
    wndClass.lpfnWndProc = WndProc
    wndClass.cbClsExtra = 0
    wndClass.cbWndExtra = 0
    wndClass.hInstance = hInstance
    wndClass.hIcon = None
    wndClass.hCursor = user32.LoadCursorW(None, ctypes.c_wchar_p(IDC_ARROW))
    wndClass.hbrBackground = ctypes.c_void_p(COLOR_WINDOW + 1)
    wndClass.lpszMenuName = None
    wndClass.lpszClassName = ctypes.c_wchar_p(className)
    wndClass.hIconSm = None

    if not user32.RegisterClassExW(ctypes.byref(wndClass)):
        raise ctypes.WinError(ctypes.get_last_error())

    hwnd = user32.CreateWindowExW(
        0,
        className,
        "Lock Cursor on Process",
        WS_OVERLAPPEDWINDOW,
        100, 100, 500, 150,
        None, None,
        hInstance,
        None
    )
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())

    WS_CHILD = 0x40000000
    WS_VISIBLE = 0x10000000
    ES_LEFT = 0x0000
    BS_PUSHBUTTON = 0x00000000
    WS_BORDER = 0x00800000

    user32.CreateWindowExW(
        0,
        "EDIT",
        "",
        WS_CHILD | WS_VISIBLE | WS_BORDER | ES_LEFT,
        20, 20, 300, 25,
        hwnd,
        wintypes.HMENU(ID_EDIT),
        hInstance,
        None
    )

    user32.CreateWindowExW(
        0,
        "BUTTON",
        "Lock Cursor",
        WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
        340, 20, 120, 25,
        hwnd,
        ctypes.c_void_p(ID_BUTTON),
        hInstance,
        None
    )

    user32.CreateWindowExW(
        0,
        "BUTTON",
        "Unlock Cursor",
        WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
        340, 60, 120, 25,
        hwnd,
        ctypes.c_void_p(ID_UNLOCK_BUTTON),
        hInstance,
        None
    )

    user32.ShowWindow(hwnd, SW_SHOW)
    user32.UpdateWindow(hwnd)

    msg = MSG()
    CLIP_REPEAT_INTERVAL = 0.1
    last_clip_time = 0

    global locked_rect, hwnd_target

    while True:
        has_msg = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
        if has_msg:
            if msg.message == WM_DESTROY:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        
        if hwnd_target:
            fg = GetForegroundWindow()
            if fg == hwnd_target:
                now = time.time()
                if now - last_clip_time > CLIP_REPEAT_INTERVAL:
                    rect = RECT()
                    if GetWindowRect(hwnd_target, ctypes.byref(rect)):
                        hMonitor = MonitorFromWindow(hwnd_target, MONITOR_DEFAULTTONEAREST)
                        monitor_info = MONITORINFO()
                        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
                        if GetMonitorInfo(hMonitor, ctypes.byref(monitor_info)):
                            if rect.left < monitor_info.rcMonitor.left:
                                rect.left = monitor_info.rcMonitor.left - 1
                            if rect.top < monitor_info.rcMonitor.top:
                                rect.top = monitor_info.rcMonitor.top - 1
                            if rect.right > monitor_info.rcMonitor.right:
                                rect.right = monitor_info.rcMonitor.right - 1
                            if rect.bottom > monitor_info.rcMonitor.bottom:
                                rect.bottom = monitor_info.rcMonitor.bottom - 1
                        locked_rect = rect
                        ClipCursor(ctypes.byref(locked_rect))
                    last_clip_time = now
            else:
                if locked_rect is not None:
                    ClipCursor(None)
                    locked_rect = None
        else:
            if locked_rect is not None:
                ClipCursor(None)
                locked_rect = None

        time.sleep(0.01)

    ClipCursor(None)

if __name__ == "__main__":
    main()
