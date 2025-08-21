import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from loguru import logger

__all__ = [
    "Pinger",
]


class Pinger:
    @classmethod
    def sync_ping(cls, ip: str, count: int = 2, timeout: int = 3) -> bool | None:
        try:
            proc = subprocess.run(
                ["ping", *cls._prepare_args(ip, count, timeout)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Failed to ping {ip}: {repr(e)}")
            return None

    @classmethod
    def multi_ping(cls, hosts: list[str], count: int = 2, timeout: int = 3, max_workers: int = 20) -> list[str]:
        """
        Пингует список хостов в несколько потоков.
        Возвращает список только доступных хостов.
        """
        alive_hosts: list[str] = []

        def ping_host(host: str) -> tuple[str, bool | None]:
            return host, cls.sync_ping(host, count, timeout)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(ping_host, host) for host in hosts]
            for future in as_completed(futures):
                host, result = future.result()
                if result is True:
                    logger.info(f"Host {host} is alive")
                    alive_hosts.append(host)
                else:
                    logger.warning(f"Host {host} is not alive")

        return alive_hosts

    @classmethod
    async def async_ping(cls, ip: str, count: int = 2, timeout: int = 3) -> bool | None:
        """
        Асинхронно проверяет доступность IP-адреса.
        Возвращает:
            - True – если устройство отвечает на ping
            - False – если устройство не отвечает
            - None – если IP некорректен или произошла ошибка выполнения ping
        """
        # Проверяем, что IP-адрес выглядит корректно
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping",
                *cls._prepare_args(ip, count, timeout),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            # Если stderr не пуст или код возврата != 0 – значит, что-то пошло не так
            if stderr or proc.returncode != 0:
                return False
            return True

        except Exception as e:  # Если команда ping не найдена или другая ошибка
            logger.error(f"Failed to ping {ip}: {repr(e)}")
            return None

    @classmethod
    def _prepare_args(cls, ip: str, count: int = 2, timeout: int = 3) -> list[str]:
        """
        Для Windows: `ping -n 1 -w {timeout * 1000} {ip}`
        Для Linux/Mac: `ping -c 1 -W {timeout} {ip}`
        """
        is_windows: bool = "nt" in os.name
        return [
            "-n" if is_windows else "-c",
            str(count),  # Один пакет (Linux/Mac)
            "-w" if is_windows else "-W",
            str(timeout),  # Таймаут (Linux/Mac)
            ip,
        ]
