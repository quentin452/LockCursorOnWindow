import ctypes
from ctypes import wintypes
import time

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_LBUTTONDOWN = 0x0201
WS_OVERLAPPEDWINDOW = 0x00CF0000
SW_SHOW = 5
COLOR_WINDOW = 5
IDC_ARROW = 32512

ID_EDIT = 101
ID_PICK_BUTTON = 104
ID_UNLOCK_BUTTON = 103  

locked_rect = None
hwnd_target = None  
picking = False
in_move = False

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

GetWindowRect = user32.GetWindowRect
GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
GetWindowRect.restype = wintypes.BOOL

ClipCursor = user32.ClipCursor
ClipCursor.argtypes = [ctypes.POINTER(RECT)]
ClipCursor.restype = wintypes.BOOL

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND
GetForegroundWindow.argtypes = []

MonitorFromWindow = user32.MonitorFromWindow
MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
MonitorFromWindow.restype = wintypes.HMONITOR

GetMonitorInfo = user32.GetMonitorInfoW
GetMonitorInfo.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
GetMonitorInfo.restype = wintypes.BOOL

user32.PostQuitMessage.argtypes = [wintypes.INT]
user32.PostQuitMessage.restype = None

def clip_cursor_to_window(hwnd):
    global locked_rect
    rect = RECT()
    if not GetWindowRect(hwnd, ctypes.byref(rect)):
        print("Erreur GetWindowRect")
        return False

    hMonitor = MonitorFromWindow(hwnd, 2)
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
    return True

@WNDPROC
def WndProc(hwnd, msg, wparam, lparam):
    global hwnd_target, locked_rect, picking
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    elif msg == WM_COMMAND:
        ctrl_id = wparam & 0xFFFF
        if ctrl_id == ID_PICK_BUTTON:
            picking = True
            user32.SetCapture(hwnd)
        elif ctrl_id == ID_UNLOCK_BUTTON:
            ClipCursor(None)
            hwnd_target = None
            locked_rect = None
            picking = False
        return 0
    elif msg == WM_LBUTTONDOWN:
        if picking:
            user32.ReleaseCapture()
            picking = False
            point = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(point))
            
            hwnd_clicked = user32.WindowFromPoint(point)
            hwnd_target = user32.GetAncestor(hwnd_clicked, 2)
            
            if hwnd_target:
                if clip_cursor_to_window(hwnd_target):
                    pass
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
    user32.LoadCursorW.restype = wintypes.HANDLE
    user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]

    wndClass.hCursor = user32.LoadCursorW(None, wintypes.LPCWSTR(IDC_ARROW))

    wndClass.hbrBackground = ctypes.c_void_p(COLOR_WINDOW + 1)
    wndClass.lpszMenuName = None
    wndClass.lpszClassName = ctypes.c_wchar_p(className)
    wndClass.hIconSm = None

    if not user32.RegisterClassExW(ctypes.byref(wndClass)):
        raise ctypes.WinError(ctypes.get_last_error())

    hwnd = user32.CreateWindowExW(
        0,
        className,
        "Lock Cursor on Window Picker",
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
    BS_PUSHBUTTON = 0x00000000

    hwnd_pick = user32.CreateWindowExW(
        0,
        "BUTTON",
        "Pick Window",
        WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
        20, 20, 150, 25,
        hwnd,
        wintypes.HMENU(ID_PICK_BUTTON),
        hInstance,
        None
    )
    if not hwnd_pick:
        raise ctypes.WinError(ctypes.get_last_error())

    user32.CreateWindowExW(
        0,
        "BUTTON",
        "Unlock Cursor",
        WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
        200, 20, 150, 25,
        hwnd,
        wintypes.HMENU(ID_UNLOCK_BUTTON),
        hInstance,
        None
    )

    user32.ShowWindow(hwnd, SW_SHOW)
    user32.UpdateWindow(hwnd)

    msg = MSG()
    CLIP_REPEAT_INTERVAL = 0.1
    last_clip_time = 0

    global locked_rect, hwnd_target, in_move

    prev_rect = RECT()
    last_change_time = 0
    STABILITY_TIMEOUT = 0.3

    while True:
        has_msg = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
        if has_msg:
            if msg.message == 0x0012:  # WM_QUIT
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if hwnd_target:
            rect = RECT()
            if GetWindowRect(hwnd_target, ctypes.byref(rect)):
                now = time.time()

                active_hwnd = GetForegroundWindow()
                if active_hwnd != hwnd_target:
                    if locked_rect is not None:
                        ClipCursor(None)
                        locked_rect = None
                else:
                    if locked_rect is None:
                        clip_cursor_to_window(hwnd_target)
                        in_move = False

                if (rect.left != prev_rect.left or rect.top != prev_rect.top or
                    rect.right != prev_rect.right or rect.bottom != prev_rect.bottom):

                    if not in_move:
                        ClipCursor(None)
                        in_move = True
                        locked_rect = None

                    last_change_time = now

                elif in_move and (now - last_change_time > STABILITY_TIMEOUT):
                    if clip_cursor_to_window(hwnd_target):
                        in_move = False

                prev_rect = rect
        else:
            if locked_rect is not None:
                ClipCursor(None)
                locked_rect = None

        time.sleep(0.01)

    ClipCursor(None)

if __name__ == "__main__":
    main()
