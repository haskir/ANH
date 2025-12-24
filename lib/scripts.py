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

_edr_server: str = "10.192.145.19"

InstallEDRRedOS: list[str] = [
    "sudo su",
    f"BZ_AUTHORITY_SERVICE={_edr_server}:9992 "
    f"BZ_SENSORS_SERVICE={_edr_server}:9991 "
    f"BZ_POLLING_PERIOD=300s "
    f"BZ_DIAL_TIMEOUT=10s "
    f"BZ_AGENT_GROUPS=LINDEF "
    f"BZ_LOG_LEVEL=debug "
    f"dnf install -y /tmp/bzsensor.rpm > /tmp/bzsensor.log",
    "exit",
]
