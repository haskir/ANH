from loguru import logger

from .ssh_connection import PasswordError, SshConnection


def process_host(
    host: str,
    username: str,
    old_passwords: list[str],
    new_password: str,
    scripts: list[list[str]] | None = None,
    only_astra: bool = False,
    only_redhat: bool = False,
) -> SshConnection | None:
    try:
        connection = SshConnection(host, username, old_passwords)
        if connection.password != new_password:
            connection.change_password(new_password, change_root_also=True)
        # connection.add_local_user_to_wheel()
        if not scripts:
            return connection
        if only_astra and not connection.is_astra:
            print(f"{host} is not astra: skip")
            return connection
        if only_redhat and connection.is_astra:
            print(f"{host} is astra: skip")
            return connection
        for script in scripts:
            connection.send_script(script)

        return connection
    except PasswordError:
        logger.error(f"Password error on {host}")
    except Exception as e:
        logger.error(f"Unexpected error on {host}: {repr(e)}")
    return None
