import json
import socket
from tkinter import messagebox
import tkinter as tk

from dotenv import load_dotenv

from chat_client.args import get_args


def register(app_settings, nickname=None) -> tuple[str, str] | None:
    """Register to chat."""
    if not nickname:
        messagebox.showerror("Ошибка", "Введите ваш никнейм")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((app_settings.host, app_settings.outport))
            conn = sock.makefile("rwb", 0)
            conn.readline()
            conn.write(b"\n")
            conn.readline()
            conn.write(f"{nickname}\n".encode())
            response = conn.readline()
        except OSError:
            messagebox.showerror("Ошибка", "Нет соединения с сервером")
            exit()

    creds = json.loads(response)
    with open("chat_client/.env", "w") as fh:
        fh.write(f"TOKEN={creds['account_hash']}")

    messagebox.showinfo(
        'Пользователь зарегистрирован', f'Добро пожаловать {creds["nickname"]}!'
    )
    print(creds["account_hash"])

    exit()


def draw(settings):
    root = tk.Tk()
    root.title("Регистрация нового пользователя")

    label = tk.Label(root, text="Введите ваш никнейм:")
    label.pack(fill="x")

    nickname = tk.StringVar()
    entry = tk.Entry(root, textvariable=nickname)
    entry.pack(fill="x", padx=20)
    entry.focus()
    entry.bind("<Return>", lambda event: register(settings, nickname.get()))

    button = tk.Button(root, text="Зарегистрировать")
    button["command"] = lambda: register(settings, nickname.get())
    button.pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    load_dotenv()
    draw(get_args())
