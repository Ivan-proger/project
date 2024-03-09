from django.core.management.base import BaseCommand
from django.core.management import call_command
from pathlib import Path

import paramiko
import os

def create_dump():
    # Создание дампа базы данных
    backup_path = Path("/path/to/backup.json")
    call_command("dumpdata", "--format=json", output=backup_path)
    return backup_path


def save_to_remote_server(backup_path, host, port, username, password):
    # Сохранение дампа на удаленный сервер

    success = False

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port, username, password)

        remote_path = "/path/to/remote/folder"
        ssh.exec_command(f"mkdir -p {remote_path}")

        sftp = ssh.open_sftp()
        sftp.put(backup_path, f"{remote_path}/{backup_path.name}")

        success = True
    except Exception as e:
        print(f"Error saving backup to remote server: {e}")
    finally:
        ssh.close()

    if success:
        backup_path.unlink()

class Command(BaseCommand):
    help = 'Backup bd'

    from dotenv import load_dotenv
    load_dotenv()
    host = os.getenv("HOST")
    port = int(os.getenv("PORT"))
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    # Автоматическое создание дампа и его передача
    backup_path = create_dump()
    save_to_remote_server(
        backup_path,
        host=host,
        port=port,
        username=username,
        password=password,
    )

