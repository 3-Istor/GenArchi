"""Labo P2 local : les rôles Ansible joués sur des conteneurs Debian 13 + systemd, sans compte GCP.

    python3 infra/p2/lab/lab.py up        # réseau 10.20.0.0/16 + conteneurs aux adresses de la vraie P2
    python3 infra/p2/lab/lab.py inventory # inventaire au format produit par OpenTofu
    python3 infra/p2/lab/lab.py down

Ce que le labo ne reproduit pas (et qui reste à tester sur GCP) : NFS noyau et bascule du disque régional
(un volume Docker partagé joue le NAS),
load balancers Google (l'IP virtuelle de PostgreSQL est jouée par HAProxy), IAP, OS Login, Cloud NAT.
"""

import json
import secrets
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NET, CIDR = "p2lab", "10.20.0.0/16"
IMAGE = "genarchi-p2lab:trixie"
SUBNETS = {"dmz": "10.20.0.0/24", "app": "10.20.1.0/24", "data": "10.20.2.0/24", "mgmt": "10.20.3.0/24"}
# Sous-ensemble de la P2 (un serveur d'app et un reverse proxy par DC, pas de NAS) : tient sur un portable.
HOSTS = {
    "monitoring": ("10.20.3.10", "c", ["zabbix"]),
    "backup": ("10.20.3.11", "c", ["barman"]),
    "rp-1": ("10.20.0.11", "a", ["reverse_proxy"]),
    "app-1a": ("10.20.1.11", "a", ["app"]),
    "app-1b": ("10.20.1.21", "b", ["app"]),
    "scheduler": ("10.20.1.30", "a", ["schedulers"]),
    "db-1": ("10.20.2.11", "a", ["db", "etcd"]),
    "db-2": ("10.20.2.21", "b", ["db", "etcd"]),
    "witness": ("10.20.2.31", "c", ["etcd", "rabbitmq", "quorum_witness"]),
    "mq-1": ("10.20.2.12", "a", ["rabbitmq"]),
    "mq-2": ("10.20.2.22", "b", ["rabbitmq"]),
}
VIP = ("dbvip", "10.20.2.5")  # HAProxy, sonde /primary de Patroni : joue le LB interne de GCP
SECRETS = HERE / ".secrets.json"


def sh(*cmd, check=True, capture=False):
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def cgroup_v2() -> bool:
    return Path("/sys/fs/cgroup/cgroup.controllers").exists()


# Le NAS est joué par un volume Docker partagé entre les serveurs d'app (pas de NFS noyau dans un conteneur).
SHARED_TICKETS = {"app-1a", "app-1b", "scheduler"}


def run_container(name, ip):
    args = ["docker", "run", "-d", "--name", f"p2lab-{name}", "--hostname", name, "--network", NET, "--ip", ip,
            "--privileged", "--tmpfs", "/run", "--tmpfs", "/run/lock", "-e", "container=docker"]
    # Docker réécrit /etc/hosts à chaque démarrage : on lui donne les mêmes entrées que le rôle common.
    for n, (h_ip, _, _) in HOSTS.items():
        args += ["--add-host", f"{n}.p2.genarchi.internal:{h_ip}", "--add-host", f"{n}:{h_ip}"]
    args += ["--add-host", f"db.p2.genarchi.internal:{VIP[1]}"]
    if name in SHARED_TICKETS:
        args += ["-v", "p2lab-tickets:/mnt/tickets"]
    if cgroup_v2():
        args += ["--cgroupns=private"]
    else:  # hôte en cgroup v1 : systemd ≥ 256 doit être forcé
        args += ["--cgroupns=host", "-v", "/sys/fs/cgroup:/sys/fs/cgroup:rw",
                 "-e", "SYSTEMD_PROC_CMDLINE=systemd.unified_cgroup_hierarchy=0 SYSTEMD_CGROUP_ENABLE_LEGACY_FORCE=1"]
    sh(*args, IMAGE)


def up():
    sh("docker", "build", "-q", "-t", IMAGE, str(HERE))
    if sh("docker", "network", "inspect", NET, check=False, capture=True).returncode:
        sh("docker", "network", "create", "--subnet", CIDR, NET)
    for name, (ip, _, _) in {**HOSTS, VIP[0]: (VIP[1], "a", [])}.items():
        if sh("docker", "inspect", f"p2lab-{name}", check=False, capture=True).returncode:
            run_container(name, ip)
    print("labo démarré :", ", ".join(HOSTS), "+", VIP[0])


def down():
    names = [f"p2lab-{n}" for n in [*HOSTS, VIP[0]]]
    sh("docker", "rm", "-f", *names, check=False, capture=True)
    sh("docker", "network", "rm", NET, check=False, capture=True)
    sh("docker", "volume", "rm", "p2lab-tickets", check=False, capture=True)


def inventory():
    if not SECRETS.exists():
        keys = ["postgres", "replicator", "rewind", "app_db", "barman", "streaming_barman", "rabbitmq_app",
                "rabbitmq_admin", "erlang_cookie", "admin_token", "staff_token", "zabbix_db", "zabbix_admin"]
        SECRETS.write_text(json.dumps({k: secrets.token_hex(16) for k in keys}))
        SECRETS.chmod(0o600)
    groups = sorted({g for _, _, gs in HOSTS.values() for g in gs})
    inv = {
        "all": {
            "vars": {
                "ansible_connection": "community.docker.docker",
                "ansible_docker_extra_args": "",
                "gcp_project": "lab",
                "gcp_region": "lab",
                "public_domain": "localhost",
                "network_cidr": CIDR,
                "subnets": SUBNETS,
                "proxy_only_cidr": "10.20.255.0/24",
                "internal_domain": "p2.genarchi.internal",
                "db_vip": VIP[1],
                "nas_vip": "10.20.2.6",
                "nas_active": "nas-1",
                "p2_hosts": {n: ip for n, (ip, _, _) in HOSTS.items()},
                "secrets": json.loads(SECRETS.read_text()),
                # Spécifique au labo
                "nfs_enabled": False,
                "pg_hba_extra": [f"host all all {VIP[1]}/32 scram-sha-256",
                                 f"host replication streaming_barman {VIP[1]}/32 scram-sha-256"],
            },
            "children": {
                g: {"hosts": {n: {"ansible_host": f"p2lab-{n}", "gcp_zone": f"lab-{z}",
                                  "datacenter": "temoin" if z == "c" else f"dc{1 if z == 'a' else 2}"}
                              for n, (_, z, gs) in HOSTS.items() if g in gs}}
                for g in groups
            } | {"lab_vip": {"hosts": {VIP[0]: {"ansible_host": f"p2lab-{VIP[0]}", "gcp_zone": "lab-a",
                                                  "datacenter": "dc1"}}}},
        }
    }
    out = HERE / "inventory.json"
    out.write_text(json.dumps(inv, indent=1))
    out.chmod(0o600)
    print(out)


if __name__ == "__main__":
    {"up": up, "down": down, "inventory": inventory}[sys.argv[1] if len(sys.argv) > 1 else "up"]()
