import asyncio
import websockets
import json
import os

clients = {}  
files = {}

async def load_files():
    if not os.path.exists("server_files"):
        os.makedirs("server_files")
    for fname in os.listdir("server_files"):
        with open(f"server_files/{fname}", 'r', encoding='utf-8') as f:
            files[fname] = f.read()

async def save_file(filename):
    with open(f"server_files/{filename}", 'w', encoding='utf-8') as f:
        f.write(files[filename])

async def broadcast_to_file_users(filename, message, exclude_ws=None):
    for ws, info in clients.items():
        if info.get("filename") == filename and ws != exclude_ws:
            try:
                await ws.send(message)
            except:
                pass

async def handler(websocket):
    print("[+] Client connected")
    clients[websocket] = {"username": None, "filename": None}

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "set_username":
                clients[websocket]["username"] = data["username"]

            elif action == "list_files":
                await websocket.send(json.dumps({
                    "action": "files_list",
                    "files": list(files.keys())
                }))

            elif action == "create_file":
                filename = data["filename"]
                if filename not in files:
                    files[filename] = ""
                    await save_file(filename)
                await broadcast_file_list()

            elif action == "delete_file":
                filename = data["filename"]
                if filename in files:
                    del files[filename]
                    try:
                        os.remove(f"server_files/{filename}")
                    except:
                        pass
                    await broadcast_file_list()

            elif action == "open_file":
                filename = data["filename"]
                clients[websocket]["filename"] = filename
                content = files.get(filename, "")
                await websocket.send(json.dumps({
                    "action": "file_content",
                    "filename": filename,
                    "content": content
                }))

            elif action in ["insert", "delete"]:
                filename = data["filename"]
                index = data["index"]
                line, col = map(int, index.split('.'))

                text = files.get(filename, "")
                lines = text.split('\n')

                if action == "insert":
                    content = data["content"]
                    while len(lines) <= line:
                        lines.append("")
                    try:
                        lines[line] = lines[line][:col] + content + lines[line][col:]
                    except IndexError:
                        lines[line] = content
                elif action == "delete":
                    length = int(data["length"])
                    try:
                        lines[line] = lines[line][:col] + lines[line][col+length:]
                    except:
                        pass

                files[filename] = '\n'.join(lines)
                await save_file(filename)

                await broadcast_to_file_users(filename, json.dumps(data), exclude_ws=websocket)

    except websockets.ConnectionClosed:
        print("[-] Client disconnected")

    finally:
        clients.pop(websocket, None)

async def broadcast_file_list():
    msg = json.dumps({
        "action": "files_list",
        "files": list(files.keys())
    })
    await asyncio.gather(*[ws.send(msg) for ws in clients])

async def main():
    await load_files()
    async with websockets.serve(handler, "localhost", 12345):
        print("[*] WebSocket Server running on ws://localhost:12345")
        await asyncio.Future()  

if __name__ == "__main__":
    asyncio.run(main())
