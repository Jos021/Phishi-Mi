#!/usr/bin/env python3
"""
Instalador do PhishiMi CTF
"""
import os
import subprocess
import sys

def check_python():
    """Verifica versão do Python"""
    print("[+] Verificando Python...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print(f"❌ Python {version.major}.{version.minor} detectado")
        print("✅ Requer Python 3.6+")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK!")
    return True

def install_dependencies():
    """Instala dependências"""
    print("\n[+] Instalando dependências...")
    
    requirements = [
        'qrcode[pil]>=7.0',
        'pillow>=9.0'
    ]
    
    for req in requirements:
        try:
            print(f"  Instalando {req}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', req])
            print(f"  ✅ {req} instalado")
        except subprocess.CalledProcessError:
            print(f"  ❌ Falha ao instalar {req}")
            return False
    
    return True

def create_directories():
    """Cria diretórios necessários"""
    print("\n[+] Criando diretórios...")
    
    directories = [
        'templates',
        'static',
        'qrcodes',
        'logs'
    ]
    
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
        print(f"  ✅ {dir_name}/")
    
    return True

def create_config():
    """Cria arquivo de configuração"""
    print("\n[+] Criando configuração...")
    
    config = '''# PhishiMi CTF Configuration
PORT = 8080
DEBUG = True
DATABASE = "captures.db"

# Templates disponíveis
TEMPLATES = [
    "facebook",
    "instagram", 
    "google",
    "netflix",
    "tiktok"
]

# Mensagens educacionais
EDUCATIONAL_WARNING = "⚠️ Esta ferramenta é para fins educacionais. Use apenas em ambiente controlado com autorização explícita."
'''
    
    with open('config.py', 'w') as f:
        f.write(config)
    
    print("  ✅ config.py criado")
    return True

def main():
    """Função principal do instalador"""
    print("""
    ╔══════════════════════════════════════════╗
    ║       Instalador PhishiMi CTF           ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Verificar Python
    if not check_python():
        sys.exit(1)
    
    # Instalar dependências
    if not install_dependencies():
        print("\n❌ Falha ao instalar dependências")
        sys.exit(1)
    
    # Criar diretórios
    if not create_directories():
        print("\n❌ Falha ao criar diretórios")
        sys.exit(1)
    
    # Criar configuração
    if not create_config():
        print("\n❌ Falha ao criar configuração")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ Instalação concluída com sucesso!")
    print("="*50)
    
    print("\n📁 Estrutura criada:")
    print("  phishimi.py          # Programa principal")
    print("  templates/           # Templates HTML")
    print("  static/              # CSS e JavaScript")
    print("  qrcodes/             # QR Codes gerados")
    print("  logs/                # Logs do sistema")
    print("  captures.db          # Banco de dados")
    
    print("\n🚀 Para executar:")
    print("  python phishimi.py")
    
    print("\n🎯 URLs de acesso:")
    print("  http://localhost:8080          # Página inicial")
    print("  http://localhost:8080/dashboard # Dashboard")
    
    print("\n⚠️  Lembre-se: Esta é uma ferramenta educacional!")
    print("   Use apenas em ambiente controlado com autorização.\n")

if __name__ == "__main__":
    main()