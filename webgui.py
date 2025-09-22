import tkinter as tk
from tkinter import simpledialog, messagebox
import asyncio
import threading
import websockets
import json

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WebSocket Collaborative Editor")

        self.ws = None
        self.loop = asyncio.new_event_loop()

        self.username = simpledialog.askstring("Login", "Enter your username:")

        self.current_file = None

        self.left_frame = tk.Frame(root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.btn_create = tk.Button(self.left_frame, text="Create File", command=self.create_file)
        self.btn_create.pack(fill=tk.X)

        self.btn_delete = tk.Button(self.left_frame, text="Delete File", command=self.delete_file)
        self.btn_delete.pack(fill=tk.X)

        self.file_listbox = tk.Listbox(self.left_frame)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        self.text = tk.Text(root, wrap="word", undo=True)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.bind("<KeyRelease>", self.on_key_release)

        threading.Thread(target=self.start_async_loop, daemon=True).start()

    def start_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())

    async def connect(self):
        async with websockets.connect("ws://localhost:12345") as self.ws:
            await self.send({"action": "set_username", "username": self.username})
            await self.send({"action": "list_files"})
            await self.listen()

    async def send(self, msg):
        if self.ws:
            await self.ws.send(json.dumps(msg))

    async def listen(self):
        async for msg in self.ws:
            data = json.loads(msg)
            self.root.after(0, self.handle_message, data)

    def send_async(self, msg):
        asyncio.run_coroutine_threadsafe(self.send(msg), self.loop)

    def create_file(self):
        fname = simpledialog.askstring("Create File", "Filename:")
        if fname:
            self.send_async({"action": "create_file", "filename": fname})

    def delete_file(self):
        selection = self.file_listbox.curselection()
        if selection:
            fname = self.file_listbox.get(selection[0])
            if messagebox.askyesno("Delete File", f"Are you sure you want to delete '{fname}'?"):
                self.send_async({"action": "delete_file", "filename": fname})
                if self.current_file == fname:
                    self.text.delete(1.0, tk.END)
                    self.current_file = None

    def on_file_select(self, event):
        sel = self.file_listbox.curselection()
        if sel:
            fname = self.file_listbox.get(sel[0])
            self.current_file = fname
            self.send_async({"action": "open_file", "filename": fname})

    def on_key_release(self, event):
        if not self.current_file:
            return

        index = self.text.index(tk.INSERT)
        if event.keysym == "BackSpace":
            self.send_async({
                "action": "delete",
                "filename": self.current_file,
                "index": index,
                "length": 1
            })
        elif event.char:
            self.send_async({
                "action": "insert",
                "filename": self.current_file,
                "index": index,
                "content": event.char
            })

    def handle_message(self, msg):
        action = msg.get("action")
        if action == "files_list":
            self.file_listbox.delete(0, tk.END)
            for f in msg.get("files", []):
                self.file_listbox.insert(tk.END, f)
        elif action == "file_content":
            self.current_file = msg.get("filename")
            self.text.delete(1.0, tk.END)
            self.text.insert(1.0, msg.get("content", ""))
        elif action == "insert":
            if msg.get("filename") == self.current_file:
                self.text.insert(msg["index"], msg["content"])
        elif action == "delete":
            if msg.get("filename") == self.current_file:
                start = msg["index"]
                end = self.text.index(f"{start}+{msg['length']}c")
                self.text.delete(start, end)

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()
