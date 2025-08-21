import re
import time

import paramiko
from loguru import logger

__all__ = ['SshConnection', 'PasswordError',]

# 7-bit C1 ANSI sequences
ansi_escape = re.compile(r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''', re.VERBOSE)


class PasswordError(Exception):
    pass


class SshConnection:
    def __init__(
            self,
            address: str,
            username: str,
            passwords: list[str],
            root_password: str = None,
            port: int = 22,
            sleep_time: int = 1,
            timeout: int = 5,
    ):
        if len(passwords) > 4:
            raise AttributeError("Слишком много паролей, возможен locked out ip")
        self.address: str = address
        self.username: str = username
        self.password: str | None = None
        self.root_password: str | None = root_password
        self.port: int = port
        self.timeout: int = timeout

        self.is_alive: bool = False

        self.client: paramiko.SSHClient | None = None
        self.channel: paramiko.Channel | None = None

        self.sleep_time: int = sleep_time
        self.__connect(passwords)

    def __connect(self, passwords: list[str]) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for password in passwords:
            try:
                client.connect(
                    hostname=self.address,
                    username=self.username,
                    password=password,
                    port=self.port,
                    timeout=self.timeout
                )
                channel = client.invoke_shell(width=230, height=50)
                channel.settimeout(self.timeout)
                self.client = client
                self.channel = channel
                self.password = password

                if not self.root_password:
                    self.root_password = self.password
                self.is_alive = True

                logger.add(
                    sink=f'logs/{self.address}.log',
                    format='{time:MMMM D > HH:mm:ss!UTC} | {level} | {message}'
                )
                logger.info(f'Connected to {self.address} with {self.password}')

                self.is_astra = self.check_is_astra()
                return
            except paramiko.ssh_exception.AuthenticationException:
                logger.debug(f'Wrong pass {password} for {self.username}@{self.address}')
            except TimeoutError:
                logger.error(f'TimeoutError for {self.username}@{self.address}')
        raise PasswordError(f'Did not find correct password for {self.username}@{self.address}')

    def check_is_astra(self) -> bool:
        self.channel.send(f'cat /etc/*rel* \n'.encode())
        time.sleep(self.sleep_time)
        result = self.channel.recv(1024).decode()
        time.sleep(self.sleep_time)
        return "astra" in result.lower()

    def _log_output(self, command: str) -> None:
        while True:
            data = ""
            try:
                if self.channel.recv_ready():
                    data += self.channel.recv(1024).decode()
                    data = ansi_escape.sub('', data)
                    data = data.replace("\r", " ").replace("\n", " ")
                    if data:
                        logger.info(f'{command = } {data = }')
                else:
                    break
            except paramiko.SSHException as ssh_e:
                logger.error(f'{self.address} -> {ssh_e}')
            except TimeoutError:
                logger.error(f'TimeoutError for {self.username}@{self.address}')
                self.is_alive = False

    def send_command(self, command):
        if not self.is_alive:
            logger.error(f'{self.address} is not alive')
            return
        if isinstance(command, list):
            for line in command:
                self.send_command(line)
        else:
            self.channel.send(command.encode() + "\n".encode())
            time.sleep(self.sleep_time)
            if "sudo" in command:
                data = self.channel.recv(1024).decode()
                logger.log("INFO", f'{data=}')
                if "пароль" in data:
                    self.channel.send(self.password.encode() + "\n".encode())
                    time.sleep(self.sleep_time)
            self._log_output(command)

    def change_password(self, new_password: str, change_root_also: bool = False) -> None:
        if self.password == new_password:
            return
        self.send_command("sudo su")
        self.send_command(f'passwd {self.username}')
        self.send_command(new_password)
        self.send_command(new_password)
        self.password = new_password
        if change_root_also:
            self.send_command(f'passwd root')
            self.send_command(new_password)
            self.send_command(new_password)
            self.root_password = new_password
        self.send_command("exit")

    def add_local_user_to_wheel(self) -> None:
        """ Add local user to wheel group """
        if not self.is_astra:
            command = 'su -c "usermod -a -G wheel fatalocal"\n'.encode()
            self.channel.send(command)
            time.sleep(5)
            self.channel.send(f'{self.password}\n'.encode())
            time.sleep(3)
            self._log_output(command.decode())