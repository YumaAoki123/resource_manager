import tkinter as tk
from tkinter import messagebox
import os
from dotenv import load_dotenv

import pickle
import os.path
import sys
from email_service import on_send_button_click, check_email

load_dotenv()


admin_username = os.environ['ADMIN_USERNAME']
admin_password = os.environ['ADMIN_PASSWORD']

print(f'admin_username:{admin_username}')

class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ウィンドウの設定
        self.title("管理者ログイン")
        self.geometry("400x300")
        
        # ログイン画面のウィジェットを作成
        self.create_login_widgets()

    def create_login_widgets(self):
        # ログイン用のフレーム
        login_frame = tk.Frame(self)
        login_frame.pack(pady=50)

        # ユーザーネームラベルとエントリー
        tk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=10, pady=10)
        self.username_entry = tk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1)

        # パスワードラベルとエントリー
        tk.Label(login_frame, text="Password:").grid(row=1, column=0, padx=10, pady=10)
        self.password_entry = tk.Entry(login_frame, show="*")
        self.password_entry.grid(row=1, column=1)

        # ログインボタン
        login_button = tk.Button(login_frame, text="Login", command=self.login)
        login_button.grid(row=2, column=0, columnspan=2, pady=10)

    def login(self):
        # 入力された情報を取得
        username = self.username_entry.get()
        password = self.password_entry.get()

        # 認証情報を確認
        if username == admin_username and password == admin_password:
            messagebox.showinfo("Login Successful", "ログインに成功しました。")
            self.open_admin_dashboard()
        else:
            messagebox.showerror("Login Failed", "ユーザー名またはパスワードが違います。")

    def open_admin_dashboard(self):
        # 現在のウィジェットをすべて破棄
        for widget in self.winfo_children():
            widget.destroy()

        # 管理者ダッシュボードを作成
        self.title("管理者ダッシュボード")
        dashboard_frame = tk.Frame(self)
        dashboard_frame.pack(pady=50)

        # タスクメール送信ボタン(テスト用)
        start_auth_button = tk.Button(dashboard_frame, text="メール一斉送信", command=on_send_button_click)
        start_auth_button.pack(pady=20)

       
        # ログアウトボタン
        logout_button = tk.Button(dashboard_frame, text="ログアウト", command=self.logout)
        logout_button.pack(pady=10)


        

    def logout(self):
        # ログアウトしてログイン画面に戻る
        self.title("管理者ログイン")
        for widget in self.winfo_children():
            widget.destroy()
        self.create_login_widgets()




# アプリケーションの起動
if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
