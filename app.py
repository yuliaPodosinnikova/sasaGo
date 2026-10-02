from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import json
import os
import random
import hashlib
import uuid

PORT = 5000
USERS_FILE = 'users.json'

# Активные сессии в памяти: { "session_id_string": "login_user" }
SESSIONS = {}

def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "sasa": {
                "password_hash": hash_password("123456"),
                "name": "СасаВротик",
                "status": "VIP Амбассадор",
                "balance": 500
            }
        }
        save_users(default_users)
        return default_users
    
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


class SasaGoHandler(SimpleHTTPRequestHandler):

    def get_current_user(self):
        """Определяет текущего пользователя по Cookie"""
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return None, None

        cookie = SimpleCookie()
        cookie.load(cookie_header)
        
        if 'session_id' in cookie:
            session_id = cookie['session_id'].value
            username = SESSIONS.get(session_id)
            if username:
                users = load_users()
                if username in users:
                    return username, users[username]
        return None, None

    def do_GET(self):
        username, user_data = self.get_current_user()

        # 1. API профиля текущего пользователя
        if self.path == '/api/user':
            if user_data:
                self.send_json_response({
                    "authenticated": True,
                    "username": username,
                    "name": user_data.get("name", username),
                    "status": user_data.get("status", "Пользователь"),
                    "balance": user_data.get("balance", 0)
                })
            else:
                self.send_json_response({"authenticated": False, "balance": 0})
            return

        # 2. Роутинг для HTML
        routes = {
            '/': 'templates/index.html',
            '/index.html': 'templates/index.html',
            '/taxi.html': 'templates/taxi.html',
            '/scooters.html': 'templates/scooters.html',
            '/invest.html': 'templates/invest.html',
            '/food.html': 'templates/food.html'
        }

        if self.path in routes:
            file_path = routes[self.path]
            if os.path.exists(file_path):
                self.serve_file(file_path, 'text/html')
            else:
                self.send_error(404, f"File not found: {file_path}")
            return

        # 3. Статика (css, js, assets)
        file_path = self.path.lstrip('/')
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.serve_file(file_path, self.get_content_type(file_path))
            return

        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404, f"Page not found: {self.path}")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(post_data.decode('utf-8'))
        except Exception:
            data = {}

        users = load_users()
        username, user_data = self.get_current_user()

        # РЕГИСТРАЦИЯ
        if self.path == '/api/register':
            login = data.get('login', '').strip().lower()
            password = data.get('password', '')
            name = data.get('name', login)

            if not login or not password:
                self.send_json_response({"status": "error", "message": "Введите логин и пароль"}, 400)
                return

            if login in users:
                self.send_json_response({"status": "error", "message": "Логин уже занят"}, 400)
                return

            users[login] = {
                "password_hash": hash_password(password),
                "name": name,
                "status": "Новичок",
                "balance": 100 # Приветственный бонус
            }
            save_users(users)

            # Создаём сессию сразу после регистрации
            session_id = str(uuid.uuid4())
            SESSIONS[session_id] = login
            self.send_json_response(
                {"status": "success", "message": "Успешная регистрация!", "balance": 100},
                cookie_id=session_id
            )
            return

        # АВТОРИЗАЦИЯ
        elif self.path == '/api/login':
            login = data.get('login', '').strip().lower()
            password = data.get('password', '')

            if login not in users or users[login]['password_hash'] != hash_password(password):
                self.send_json_response({"status": "error", "message": "Неверный логин или пароль"}, 401)
                return

            session_id = str(uuid.uuid4())
            SESSIONS[session_id] = login
            self.send_json_response(
                {"status": "success", "message": "Вход выполнен!"},
                cookie_id=session_id
            )
            return

        # ВЫХОД (LOGOUT)
        elif self.path == '/api/logout':
            cookie_header = self.headers.get('Cookie')
            if cookie_header:
                cookie = SimpleCookie(cookie_header)
                if 'session_id' in cookie:
                    SESSIONS.pop(cookie['session_id'].value, None)
            self.send_json_response({"status": "success"})
            return

        # ДЕЙСТВИЯ С БАЛАНСОМ
        if not user_data:
            self.send_json_response({"status": "error", "message": "Авторизуйтесь!"}, 401)
            return

        if self.path == '/api/taxi/order':
            price = data.get('price', 0)
            use_points = data.get('use_points', False)
            discount = 0

            if use_points:
                discount = min(user_data['balance'], price)
                user_data['balance'] -= discount
                save_users(users)

            self.send_json_response({
                "status": "success",
                "final_price": price - discount,
                "new_balance": user_data['balance']
            })
            return

        elif self.path == '/api/scooters/order':
            total_price = data.get('total_price', 0)
            cashback = int(total_price * 0.10)
            user_data['balance'] += cashback
            save_users(users)

            self.send_json_response({
                "status": "success",
                "cashback_added": cashback,
                "new_balance": user_data['balance']
            })
            return

        elif self.path == '/api/invest/claim-bonus':
            bonus = 50
            user_data['balance'] += bonus
            save_users(users)

            self.send_json_response({
                "status": "success",
                "bonus_added": bonus,
                "new_balance": user_data['balance']
            })
            return

        self.send_error(404, "API endpoint not found")

    def send_json_response(self, data_dict, code=200, cookie_id=None):
        body = json.dumps(data_dict, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        
        if cookie_id:
            self.send_header('Set-Cookie', f'session_id={cookie_id}; Path=/; HttpOnly')

        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            header_type = f"{content_type}; charset=utf-8" if "text" in content_type or "javascript" in content_type else content_type
            self.send_header('Content-Type', header_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Server File Error: {e}")

    def get_content_type(self, path):
        if path.endswith('.css'): return 'text/css'
        if path.endswith('.js'): return 'application/javascript'
        if path.endswith('.png'): return 'image/png'
        if path.endswith('.jpg') or path.endswith('.jpeg'): return 'image/jpeg'
        if path.endswith('.svg'): return 'image/svg+xml'
        if path.endswith('.html'): return 'text/html'
        return 'text/plain'


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = HTTPServer(('127.0.0.1', PORT), SasaGoHandler)
    print(f"Сервер с авторизацией запущен: http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")