# Image des « VM » du labo P2 : Debian 13 + systemd, comme l'image debian-13 de GCE.
FROM mirror.gcr.io/library/debian:trixie
# Comme sur GCE, les paquets démarrent leurs services à l'installation (pas de policy-rc.d).
# Autorités de certification supplémentaires (proxy d'entreprise) : déposer des .crt dans ca/.
COPY ca/ /usr/local/share/ca-certificates/extra/
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      systemd systemd-sysv dbus python3 sudo ca-certificates iproute2 procps \
 && update-ca-certificates \
 && printf '[global]\ncert = /etc/ssl/certs/ca-certificates.crt\n' > /etc/pip.conf \
 && rm -rf /var/lib/apt/lists/* /usr/sbin/policy-rc.d \
 && systemctl mask systemd-logind.service getty.target console-getty.service systemd-firstboot.service
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
