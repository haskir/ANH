import re
import time

import paramiko
from loguru import logger

from .scripts import get_install_script

__all__ = [
    "SshConnection",
    "PasswordError",
]

# 7-bit C1 ANSI sequences
ansi_escape = re.compile(
    r"""
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
""",
    re.VERBOSE,
)


class PasswordError(Exception):
    pass


class SshConnection:
    def __init__(
        self,
        address: str,
        username: str,
        passwords: list[str],
        port: int = 22,
        sleep_time: int = 1,
        timeout: int = 5,
    ):
        if len(passwords) > 4:
            raise AttributeError("Слишком много паролей, возможен locked out ip")
        self.address: str = address
        self.username: str = username
        self.password: str = ""
        self.port: int = port
        self.timeout: int = timeout

        self.is_alive: bool = False

        self._client: paramiko.SSHClient | None = None
        self._channel: paramiko.Channel | None = None

        self.sleep_time: int = sleep_time
        self._connect(passwords)

    @property
    def client(self) -> paramiko.SSHClient:
        if not self._client:
            raise RuntimeError("Client is not connected")
        return self._client

    @property
    def channel(self) -> paramiko.Channel:
        if not self._channel:
            raise RuntimeError("Channel is not connected")
        return self._channel

    def _connect(self, passwords: list[str]) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for password in passwords:
            try:
                client.connect(
                    hostname=self.address,
                    username=self.username,
                    password=password,
                    port=self.port,
                    timeout=self.timeout,
                )
                channel: paramiko.Channel = client.invoke_shell(width=230, height=50)
                channel.settimeout(self.timeout)
                self._client = client
                self._channel = channel
                self.password = password
                self.is_alive = True

                logger.add(
                    sink=f"logs/{self.address}.log",
                    format="{time:MMMM D > HH:mm:ss!UTC} | {level} | {message}",
                )
                logger.info(f"Connected to {self.address}")

                self.is_astra: bool = self.check_is_astra()
                return
            except paramiko.AuthenticationException:
                logger.debug(
                    f"Wrong pass {password} for {self.username}@{self.address}"
                )
            except TimeoutError:
                logger.error(f"TimeoutError for {self.username}@{self.address}")
        raise PasswordError(
            f"Did not find correct password for {self.username}@{self.address}"
        )

    def check_is_astra(self) -> bool:
        self.channel.send("cat /etc/*rel* \n".encode())
        time.sleep(self.sleep_time)
        result = self.channel.recv(1024).decode()
        time.sleep(self.sleep_time)
        return "astra" in result.lower()

    def _log_output(self, command: str) -> None:
        while True:
            data: str = ""
            try:
                if self.channel.recv_ready():
                    data += self.channel.recv(1024).decode()
                    data = ansi_escape.sub("", data)
                    data = data.replace("\r", " ").replace("\n", " ")
                    if data:
                        logger.info(f"{command = } {data = }")
                else:
                    break
            except paramiko.SSHException as ssh_e:
                logger.error(f"{self.address} -> {ssh_e}")
            except TimeoutError:
                logger.error(f"TimeoutError for {self.username}@{self.address}")
                self.is_alive = False

    def send_script(self, script: list[str]) -> None:
        for line in script:
            self.send_command(line)

    def send_command(self, command: str, timeout: int = 60) -> str:
        """
        Универсальный метод отправки команды.
        Автоматически обрабатывает запрос пароля sudo.
        """
        if not self.is_alive:
            return ""

        # Очищаем входной буфер перед новой командой
        if self.channel.recv_ready():
            self.channel.recv(1024)

        logger.info(f"Executing: {command}")
        self.channel.send(f"{command}\n".encode())

        full_output = ""
        end_time = time.time() + timeout

        while time.time() < end_time:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode("utf-8", errors="ignore")
                clean_chunk = self._clean_output(chunk)
                full_output += clean_chunk

                # Печатаем в лог только если есть текст
                if clean_chunk.strip():
                    for line in clean_chunk.splitlines():
                        if line.strip():
                            logger.debug(f"[{self.address}] {line}")

                # Обработка запроса пароля для sudo
                if any(
                    p in clean_chunk.lower() for p in ["password", "пароль", "[sudo]"]
                ):
                    self.channel.send(f"{self.password}\n".encode())

                # Если видим промпт (завершение команды)
                # Обычно это символ $ или # в конце строки
                if full_output.strip().endswith(("$", "#", ">")):
                    break

            time.sleep(0.2)

        return full_output

    def _clean_output(self, data: str) -> str:
        """Очистка строк от ANSI и лишних символов возврата каретки"""
        data = ansi_escape.sub("", data)
        return data.replace("\r", "")

    def run_installer(self):
        """Загружает скрипт через SFTP и запускает его"""
        script_content = get_install_script()
        remote_path = "/tmp/install_edr.sh"

        try:
            # 1. Загрузка через SFTP (самый надежный метод)
            logger.info(f"[{self.address}] Uploading script via SFTP...")
            sftp = self.client.open_sftp()
            with sftp.file(remote_path, "w") as f:
                f.write(script_content)
            sftp.chmod(remote_path, 0o755)
            sftp.close()

            # 2. Запуск скрипта
            # Используем sudo -S, чтобы он читал пароль из stdin
            logger.info(f"[{self.address}] Running installation script...")
            # nohup позволит скрипту доработать, даже если SSH отвалится
            # Но мы подождем выполнения, чтобы увидеть результат
            command = "sudo -S /tmp/install_edr.sh"
            result = self.send_command(command, timeout=300)
            # Таймаут 5 минут на установку

            if "SUCCESS" in result:
                logger.success(f"[{self.address}] EDR installed successfully!")
            else:
                logger.error(
                    f"[{self.address}] Installation might have failed. Check logs."
                )

            # 3. Удаляем скрипт за собой
            self.send_command(f"rm -f {remote_path}")

        except Exception as e:
            logger.exception(
                f"[{self.address}] Critical error during installation: {e}"
            )

    def change_password(
        self,
        new_password: str,
        change_root_also: bool = False,
    ) -> None:
        if self.password == new_password:
            return
        self.send_command("sudo su")
        self.send_command(f"passwd {self.username}")
        self.send_command(new_password)
        self.send_command(new_password)
        self.password = new_password
        if change_root_also:
            self.send_command("passwd root")
            self.send_command(new_password)
            self.send_command(new_password)
        self.send_command("exit")

    def add_local_user_to_wheel(self) -> None:
        """Add local user to wheel group"""
        if not self.is_astra:
            command = 'su -c "usermod -a -G wheel fatalocal"\n'.encode()
            self.channel.send(command)
            time.sleep(self.sleep_time * 2)
            self.channel.send(f"{self.password}\n".encode())
            time.sleep(self.sleep_time)
            self._log_output(command.decode())
            self.send_command("exit")
            self._connect([self.password])
