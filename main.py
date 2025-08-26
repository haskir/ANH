import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

from lib.scripts import SetTimeSync
from lib.ssh_connection import SshConnection, PasswordError
from utils import Pinger


def load_alive_hosts(filename: str) -> list[str]:
    with open(filename) as f:
        hosts = [line.strip() for line in f if line.strip()]

    return Pinger.multi_ping(hosts)


def process_host(
    host: str,
    username: str,
    old_passwords: list[str],
    new_password: str,
    scripts: list[list[str]] = None,
) -> SshConnection | None:
    def process_script(sc: list[str]) -> None:
        for cmd in sc:
            connection.send_command(cmd)

    try:
        connection = SshConnection(host, username, old_passwords)
        if connection.password != new_password:
            connection.change_password(new_password, change_root_also=True)
        connection.add_local_user_to_wheel()
        if scripts:
            for script in scripts:
                process_script(script)

        return connection
    except PasswordError:
        logger.error(f"Password error on {host}")
    except Exception as e:
        logger.error(f"Unexpected error on {host}: {repr(e)}")
    return None


def main(username: str, old_passwords: list[str], new_password: str, host_file: str):
    max_workers: int = 8
    hosts_info: dict[str, tuple[str, bool]] = {}
    dt_format: str = "%d.%m.%Y %H:%M:%S"
    print(f"{datetime.now().strftime(dt_format)} Start")
    alive_hosts: list[str] = load_alive_hosts(host_file)
    print(f"{datetime.now().strftime(dt_format)} Alive hosts: {len(alive_hosts)}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_host,
                host=host,
                username=username,
                old_passwords=old_passwords,
                new_password=new_password,
                scripts=[SetTimeSync],
            )
            for host in alive_hosts
        ]
        for future in as_completed(futures):
            result: SshConnection = future.result()
            if result:
                pass
                # hosts_info[result.address] = (result.password, result.is_astra)

    with open("results/hosts_is_astra.json", "w") as f:
        json.dump(hosts_info, f, ensure_ascii=False, indent=2)


def creds() -> tuple[str, list[str], str]:
    load_dotenv()
    username: str = os.getenv("USER_NAME")
    old_passwords: list[str] = os.getenv("OLD_PASSWORDS", "").split(",")
    new_password: str = os.getenv("NEW_PASSWORD")
    return username, old_passwords, new_password


if __name__ == "__main__":
    main(*creds(), host_file="hosts1.txt")
