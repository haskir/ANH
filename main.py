import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from dotenv import load_dotenv

from lib.scenarios import process_host
from lib.scripts import InstallEDRRedOS
from lib.ssh_connection import SshConnection
from utils import Pinger


def load_alive_hosts(filename: str) -> list[str]:
    with open(filename) as f:
        hosts = [line.strip() for line in f if line.strip()]

    return Pinger.multi_ping(hosts)


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
                scripts=[InstallEDRRedOS],
                only_redhat=True,
            )
            for host in alive_hosts
        ]
        for future in as_completed(futures):
            result: SshConnection | None = future.result()
            if result:
                pass
                # hosts_info[result.address] = (result.password, result.is_astra)

    with open("results/hosts_is_astra.json", "w") as f:
        json.dump(hosts_info, f, ensure_ascii=False, indent=2)


def creds() -> tuple[str, list[str], str]:
    load_dotenv()
    username: str = os.getenv("USER_NAME") or ""
    old_passwords: list[str] = os.getenv("OLD_PASSWORDS", "").split(",")
    new_password: str = os.getenv("NEW_PASSWORD") or ""
    return username, old_passwords, new_password


if __name__ == "__main__":
    main(*creds(), host_file="hosts1.txt")
