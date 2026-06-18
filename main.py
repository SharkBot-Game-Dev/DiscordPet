import tkinter as tk
import json
import os
import random
import time
import ctypes
from ctypes import wintypes
from pynput import mouse, keyboard

SAVE_FILE = "pet_data.json"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def get_active_window_process_and_rect():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None, None
    
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    process_name = ""
    if pid.value != 0:
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_process:
            try:
                size = wintypes.DWORD(260)
                buff = ctypes.create_unicode_buffer(size.value)
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_process, 0, buff, ctypes.byref(size)):
                    process_name = os.path.basename(buff.value).lower()
            finally:
                kernel32.CloseHandle(h_process)
    
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    
    return process_name, rect

class DiscordPet:
    def __init__(self, root, image_path):
        self.root = root

        self.rel_x = None 
        self.rel_y = None
        
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.mouse_down_x = 0
        self.mouse_down_y = 0
        self.is_dragging = False
        
        self.coins = 0
        self.load_data()
        
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", "black")
        self.root.config(bg="black")

        orig_img = tk.PhotoImage(file=image_path)
        self.img = orig_img.subsample(2, 2) 
        
        self.label = tk.Label(root, image=self.img, bg="black")
        self.label.pack()
        
        self.coin_label = tk.Label(root, text=f"🪙 {self.coins}", fg="gold", bg="black", font=("Arial", 10, "bold"))
        self.coin_label.pack()

        self.label.bind("<Button-1>", self.on_mouse_down)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="なでる (コイン+1)", command=self.menu_pet)
        self.menu.add_separator()
        self.menu.add_command(label="終了", command=self.root.quit)

        self.pet_width = max(self.img.width(), self.coin_label.winfo_reqwidth())
        self.pet_height = self.img.height() + self.coin_label.winfo_reqheight()

        self.update_position()
        self.start_input_listeners()

    def load_data(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    self.coins = data.get("coins", 0)
                    self.rel_x = data.get("rel_x", None)
                    self.rel_y = data.get("rel_y", None)
            except:
                pass

    def save_data(self):
        with open(SAVE_FILE, "w") as f:
            json.dump({
                "coins": self.coins,
                "rel_x": self.rel_x,
                "rel_y": self.rel_y
            }, f)

    def add_coins(self, amount):
        self.coins += amount
        self.coin_label.config(text=f"🪙 {self.coins}")
        self.save_data()

    def on_mouse_down(self, event):
        self.mouse_down_x = event.x_root
        self.mouse_down_y = event.y_root
        
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.is_dragging = False

    def on_drag(self, event):
        if not self.is_dragging and (abs(event.x_root - self.mouse_down_x) > 3 or abs(event.y_root - self.mouse_down_y) > 3):
            self.is_dragging = True
            
        if self.is_dragging:
            proc_name, rect = get_active_window_process_and_rect()
            if proc_name == "discord.exe":
                new_pet_x = event.x_root - self.drag_start_x
                new_pet_y = event.y_root - self.drag_start_y
                
                new_pet_x = max(rect.left, min(new_pet_x, rect.right - self.pet_width))
                new_pet_y = max(rect.top, min(new_pet_y, rect.bottom - self.pet_height))
                
                self.rel_x = new_pet_x - rect.left
                self.rel_y = new_pet_y - rect.top
                
                self.root.geometry(f"{self.pet_width}x{self.pet_height}+{new_pet_x}+{new_pet_y}")

    def on_mouse_up(self, event):
        if not self.is_dragging:
            self.show_menu(event)
        else:
            self.is_dragging = False
            self.save_data()

    def update_position(self):
        if not self.is_dragging:
            proc_name, rect = get_active_window_process_and_rect()
            
            if proc_name == "discord.exe":
                d_width = rect.right - rect.left
                d_height = rect.bottom - rect.top
                
                if self.rel_x is None or self.rel_y is None or self.rel_x > d_width or self.rel_y > d_height:
                    self.rel_x = d_width - self.pet_width - 20
                    self.rel_y = d_height - self.pet_height - 65
                
                target_x = rect.left + self.rel_x
                target_y = rect.top + self.rel_y
                
                self.root.geometry(f"{self.pet_width}x{self.pet_height}+{target_x}+{target_y}")
                self.root.deiconify()
            else:
                self.menu.unpost()
                self.root.withdraw()

        self.root.after(100, self.update_position)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def menu_pet(self):
        self.add_coins(1)

    def check_and_earn(self):
        try:
            proc_name, _ = get_active_window_process_and_rect()
            if proc_name == "discord.exe":
                self.add_coins(1)
        except Exception as e:
            pass

    def start_input_listeners(self):
        mouse_listener = mouse.Listener(on_click=lambda x, y, button, pressed: self.check_and_earn() if pressed else None)
        mouse_listener.start()
        
        keyboard_listener = keyboard.Listener(on_press=lambda key: self.check_and_earn())
        keyboard_listener.start()

    def update_position(self):
        proc_name, rect = get_active_window_process_and_rect()
        
        if proc_name == "discord.exe":
            d_width = rect.right - rect.left
            d_height = rect.bottom - rect.top
            
            if self.rel_x is None or self.rel_y is None or self.rel_x > d_width or self.rel_y > d_height:
                self.rel_x = d_width - self.pet_width - 20
                self.rel_y = d_height - self.pet_height - 65
            
            target_x = rect.left + self.rel_x
            target_y = rect.top + self.rel_y
            
            self.root.geometry(f"{self.pet_width}x{self.pet_height}+{target_x}+{target_y}")
            self.root.deiconify()
        else:
            self.menu.unpost()
            self.root.withdraw()

        self.root.after(100, self.update_position)

if __name__ == "__main__":
    root = tk.Tk()
    image_file = "assets/pet.png"
    
    try:
        app = DiscordPet(root, image_file)
        print("Ready.")
        root.mainloop()
    except Exception as e:
        print(f"エラー: {e}")