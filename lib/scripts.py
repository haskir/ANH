_time_settings: str = "\n".join(
    [
        "[Time]",
        "NTP=ntp.favt.ru",
        "FallbackNTP=ntp.favt.ru",
        "RootDistanceMaxSec=5000",
        "#PollIntervalMinSec=32",
        "#PollIntervalMaxSec=2048",
    ]
)
SetTimeSync: list[str] = [
    f"echo '{_time_settings}' | sudo tee /etc/systemd/timesyncd.conf >/dev/null",
    "sudo systemctl disable ntpd --now",
    "sudo systemctl disable chronyd --now",
    "sudo timedatectl set-ntp true",
    "sudo systemctl restart systemd-timesyncd",
]


DownloadOpenRSA: list[str] = [
    "mkdir /home/fatalocal/.ssh;wget http://proxy.fata.ru/rsa.pub "
    "-xO /home/fatalocal/.ssh/authorized_keys;chmod 600 "
    "/home/fatalocal/.ssh/authorized_keys;chmod 700 /home/fatalocal/.ssh/;",
]
CronRSAUploader: list[str] = [
    "sudo su",
    """echo "@reboot wget http://proxy.fata.ru/rsa.pub -xO /home/fatalocal/.ssh/authorized_keys" >> /etc/crontab""",
    """echo "@reboot chmod 700 /home/fatalocal/.ssh/authorized_keys" >> /etc/crontab""",
    "chown fatalocal:fatalocal /home/fatalocal/.ssh/authorized_keys",
    "systemctl enable crond",
    "systemctl start crond",
    "exit",
]
HelloWorld: list[str] = ["echo 'Hello World!'", "ls asdsdfg"]
DeleteDrweb: list[str] = [
    "sudo nohup /opt/drweb.com/bin/remove.sh --non-interactive &",
]

_web_server: str = "10.192.0.172"
_edr_server: str = "10.192.145.19"


def get_install_script(
    web_server: str = _web_server,
    server_ip: str = _edr_server,
) -> str:
    # Используем одинарные кавычки для обертки f-строки, чтобы внутри были двойные
    return f"""#!/bin/bash
# Логируем все действия в файл на хосте для отладки
exec > /tmp/edr_install.log 2>&1

echo "--- Start Installation: $(date) ---"

echo "Downloading RPM..."
wget http://{web_server}/bzsensor.rpm -q -O /tmp/bzsensor.rpm
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download RPM from {web_server}"
    exit 1
fi

export BZ_AUTHORITY_SERVICE={server_ip}:9992
export BZ_SENSORS_SERVICE={server_ip}:9991
export BZ_POLLING_PERIOD=300s
export BZ_DIAL_TIMEOUT=10s
export BZ_AGENT_GROUPS=LINDEF
export BZ_LOG_LEVEL=debug

echo "Installing RPM via DNF..."
dnf install -y /tmp/bzsensor.rpm
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "SUCCESS: EDR installed successfully."
    rm -f /tmp/bzsensor.rpm
else
    echo "ERROR: Installation failed with exit code $RESULT"
fi

echo "--- Finished: $(date) ---"
exit $RESULT
"""
