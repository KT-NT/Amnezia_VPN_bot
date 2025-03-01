import os
import subprocess
import configparser
import json
import pytz
import socket
import logging
import tempfile
import paramiko
import getpass
import threading
import time
import bcrypt
from datetime import datetime, timedelta

# Константы для файлов
EXPIRATIONS_FILE = 'files/expirations.json'
SERVERS_FILE = 'files/servers.json'
UTC = pytz.UTC

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функции для работы с серверами
def load_servers():
    if not os.path.exists(SERVERS_FILE):
        return {}
    with open(SERVERS_FILE, 'r') as f:
        return json.load(f)

def save_servers(servers):
    os.makedirs(os.path.dirname(SERVERS_FILE), exist_ok=True)
    with open(SERVERS_FILE, 'w') as f:
        json.dump(servers, f)

def add_server(server_id, host, port, username, auth_type, password=None, key_path=None):
    servers = load_servers()
    server_config = {
        'host': host,
        'port': port,
        'username': username,
        'auth_type': auth_type,
        'password': hash_password(password) if auth_type == 'password' else None,
        '_original_password': password if auth_type == 'password' else None,
        'key_path': key_path if auth_type == 'key' else None,
        'docker_container': 'amnezia-awg',
        'wg_config_file': '/opt/amnezia/awg/wg0.conf',
        'endpoint': None,
        'is_remote': 'true'
    }
    servers[server_id] = server_config
    save_servers(servers)
    
    try:
        ssh = SSHManager(
            server_id=server_id,
            host=host,
            port=int(port),
            username=username,
            auth_type=auth_type,
            password=password,
            key_path=key_path
        )
        if ssh.connect():
            output, error = ssh.execute_command("curl -s https://api.ipify.org")
            if output and not error:
                server_config['endpoint'] = output.strip()
                servers[server_id] = server_config
                save_servers(servers)
    except Exception as e:
        logger.error(f"Не удалось получить endpoint для сервера {server_id}: {e}")
    
    return server_config

def remove_server(server_id):
    try:
        servers = load_servers()
        if server_id not in servers:
            logger.error(f"Сервер {server_id} не найден")
            return False

        server_config = servers[server_id]
        
        expirations = load_expirations()
        for username in list(expirations.keys()):
            if server_id in expirations[username]:
                del expirations[username][server_id]
                if not expirations[username]:
                    del expirations[username]
        save_expirations(expirations)

        if server_id in SSHManager._instances:
            SSHManager._instances[server_id].close()
            del SSHManager._instances[server_id]

        del servers[server_id]
        save_servers(servers)

        pwd = os.getcwd()
        users_dir = f"{pwd}/users"
        if os.path.exists(users_dir):
            for user_dir in os.listdir(users_dir):
                user_path = os.path.join(users_dir, user_dir)
                if os.path.isdir(user_path):
                    try:
                        for file in os.listdir(user_path):
                            file_path = os.path.join(user_path, file)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        os.rmdir(user_path)
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файлов пользователя {user_dir}: {e}")

        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера {server_id}: {e}")
        return False

def get_server_list():
    return list(load_servers().keys())

# Класс для управления SSH
class SSHManager:
    _instances = {}

    def __new__(cls, server_id=None, *args, **kwargs):
        if server_id not in cls._instances:
            cls._instances[server_id] = super(SSHManager, cls).__new__(cls)
            cls._instances[server_id].client = None
            cls._instances[server_id].initialized = False
        return cls._instances[server_id]

    def __init__(self, server_id=None, host=None, port=None, username=None, auth_type=None, password=None, key_path=None):
        if not getattr(self, 'initialized', False):
            self.client = None
            self.server_id = server_id
            self.host = host
            self.port = port
            self.username = username
            self.auth_type = auth_type
            self.key_path = key_path
            self.password = password
            self.initialized = True
        if password is not None:
            self.password = password

    def load_settings_from_config(self):
        try:
            servers = load_servers()
            if self.server_id in servers:
                server = servers[self.server_id]
                self.host = server['host']
                self.port = int(server['port'])
                self.username = server['username']
                self.auth_type = server['auth_type']
                if self.auth_type == 'password':
                    if not self.password:
                        self.password = server.get('_original_password')
                        if not self.password:
                            logger.error("Пароль не установлен")
                            return False
                else:
                    self.key_path = server['key_path']
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек SSH: {e}")
            return False

    def ensure_connection(self):
        if not self.client or not self.client.get_transport() or not self.client.get_transport().is_active():
            if not all([self.host, self.port, self.username, self.auth_type]):
                if not self.load_settings_from_config():
                    logger.error("Не удалось загрузить настройки SSH из конфигурации")
                    return False

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                if self.auth_type == "password":
                    self.client.connect(
                        self.host,
                        self.port,
                        self.username,
                        self.password,
                        timeout=10,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    
                    if not hasattr(self, '_original_password'):
                        self._original_password = self.password
                    else:
                        self.password = self._original_password
                else:
                    private_key = paramiko.RSAKey.from_private_key_file(self.key_path)
                    self.client.connect(
                        self.host,
                        self.port,
                        self.username,
                        pkey=private_key,
                        timeout=10,
                        look_for_keys=False,
                        allow_agent=False
                    )
                return True
            except Exception as e:
                logger.error(f"Ошибка подключения SSH: {e}")
                return False
        return True

    def execute_command(self, command):
        try:
            if not self.ensure_connection():
                return None, "Failed to establish SSH connection"
            
            stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            output = stdout.read().decode()
            error = stderr.read().decode()
            return output, error
        except Exception as e:
            logger.error(f"Ошибка выполнения команды: {e}")
            self.client = None
            return None, str(e)

    def connect(self):
        if not all([self.host, self.port, self.username, self.auth_type]):
            if not self.load_settings_from_config():
                logger.error("Не все параметры подключения установлены")
                return False
        return self.ensure_connection()

    def close(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None

# Функции для работы с Docker
def execute_docker_command(command, server_id=None):
    if server_id is None:
        raise Exception("Server ID is required")
    setting = get_config(server_id=server_id)
    if setting.get("is_remote") == "true":
        try:
            servers = load_servers()
            server_config = servers.get(server_id, {})
            
            if server_id in SSHManager._instances and hasattr(SSHManager._instances[server_id], '_original_password'):
                ssh = SSHManager._instances[server_id]
            else:
                ssh = SSHManager(
                    server_id=server_id,
                    host=server_config.get('host'),
                    port=int(server_config.get('port', 22)),
                    username=server_config.get('username'),
                    auth_type=server_config.get('auth_type'),
                    key_path=server_config.get('key_path'),
                    password=server_config.get('_original_password')
                )
            if not ssh.ensure_connection():
                raise Exception("Не удалось установить SSH подключение")

            output, error = ssh.execute_command(command)
            if error and ('error' in error.lower() or 'command not found' in error.lower()):
                raise Exception(error)
            if output is None:
                raise Exception("Failed to execute command")
            return output
        except Exception as e:
            raise Exception(f"SSH command failed: {e}")
    else:
        return subprocess.check_output(command, shell=True).decode()

# Функции для работы с WireGuard и клиентами
def get_client_list(server_id=None):
    if server_id is None:
        return []
    setting = get_config(server_id=server_id)
    wg_config_file = setting['wg_config_file']
    docker_container = setting['docker_container']
    is_remote = setting.get('is_remote') == 'true'

    client_map = get_clients_from_clients_table(server_id=server_id)

    try:
        if is_remote:
            servers = load_servers()
            server_config = servers.get(server_id, {})
            
            if server_id in SSHManager._instances and hasattr(SSHManager._instances[server_id], '_original_password'):
                ssh = SSHManager._instances[server_id]
            else:
                ssh = SSHManager(
                    server_id=server_id,
                    host=server_config.get('host'),
                    port=int(server_config.get('port', 22)),
                    username=server_config.get('username'),
                    auth_type=server_config.get('auth_type'),
                    key_path=server_config.get('key_path'),
                    password=server_config.get('_original_password')
                )
            if not ssh.connect():
                logger.error("Не удалось установить SSH соединение")
                return []
        cmd = f"docker exec -i {docker_container} cat {wg_config_file}"
        config_content = execute_docker_command(cmd, server_id=server_id)

        clients = []
        lines = config_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('[Peer]'):
                client_public_key = ''
                allowed_ips = ''
                client_name = 'Unknown'
                i += 1
                while i < len(lines):
                    peer_line = lines[i].strip()
                    if peer_line == '':
                        break
                    if peer_line.startswith('#'):
                        full_client_name = peer_line[1:].strip()
                        client_name = parse_client_name(full_client_name)
                    elif peer_line.startswith('PublicKey ='):
                        client_public_key = peer_line.split('=', 1)[1].strip()
                    elif peer_line.startswith('AllowedIPs ='):
                        allowed_ips = peer_line.split('=', 1)[1].strip()
                    i += 1
                client_name = client_map.get(client_public_key, client_name if 'client_name' in locals() else 'Unknown')
                clients.append([client_name, client_public_key, allowed_ips])
            else:
                i += 1
        return clients
    except Exception as e:
        logger.error(f"Ошибка при получении списка клиентов: {e}")
        return []

# Функции для работы с истечением срока действия и ограничениями трафика
def load_expirations():
    if not os.path.exists(EXPIRATIONS_FILE):
        return {}
    with open(EXPIRATIONS_FILE, 'r') as f:
        try:
            data = json.load(f)
            if data and not isinstance(next(iter(data.values())), dict):
                new_data = {}
                for user, info in data.items():
                    if isinstance(info, dict):
                        new_data[user] = {'default': info}
                    else:
                        new_data[user] = {'default': {
                            'expiration_time': info.get('expiration_time'),
                            'traffic_limit': info.get('traffic_limit', "Неограниченно")
                        }}
                data = new_data
            
            for user, servers in data.items():
                for server_id, info in servers.items():
                    if info.get('expiration_time'):
                        data[user][server_id]['expiration_time'] = datetime.fromisoformat(info['expiration_time']).replace(tzinfo=UTC)
                    else:
                        data[user][server_id]['expiration_time'] = None
            return data
        except json.JSONDecodeError:
            logger.error("Ошибка при загрузке expirations.json.")
            return {}

def save_expirations(expirations):
    os.makedirs(os.path.dirname(EXPIRATIONS_FILE), exist_ok=True)
    data = {}
    for user, servers in expirations.items():
        data[user] = {}
        for server_id, info in servers.items():
            data[user][server_id] = {
                'expiration_time': info['expiration_time'].isoformat() if info['expiration_time'] else None,
                'traffic_limit': info.get('traffic_limit', "Неограниченно")
            }
    with open(EXPIRATIONS_FILE, 'w') as f:
        json.dump(data, f)

# Остальные функции (create_config, get_config, root_add, deactive_user_db и т.д.) также должны быть добавлены.
