"""Configuration idempotente de Zabbix 7.0 par son API (exécutée sur la VM monitoring par Ansible).

- remplace le mot de passe par défaut du compte Admin ;
- crée l'action d'auto-enregistrement : tout agent dont la métadonnée contient « genarchi » devient un hôte
  surveillé avec le modèle « Linux by Zabbix agent active » ;
- ajoute un scénario web sur l'URL publique (le parcours client vu de l'intérieur) ;
- si un webhook Discord est fourni, active le type de média Discord et l'action d'alerte par défaut.
Affiche « changed » si quelque chose a été modifié.
"""

import argparse
import json
import os
import sys
import urllib.request

DEFAULT_PASSWORD = "zabbix"  # mot de passe livré par Zabbix, remplacé au premier passage
changed = False


def call(url, method, params, token=None):
    req = urllib.request.Request(
        url,
        data=json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode(),
        headers={"Content-Type": "application/json-rpc", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (URL locale fournie par Ansible)
        body = json.load(r)
    if "error" in body:
        raise RuntimeError(f"{method}: {body['error']}")
    return body["result"]


def login(url, password):
    for pw in (password, DEFAULT_PASSWORD):
        try:
            return call(url, "user.login", {"username": "Admin", "password": pw}), pw
        except RuntimeError:
            continue
    sys.exit("connexion impossible au compte Admin")


def main():
    global changed
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--discord-webhook", default="")
    p.add_argument("--public-url", required=True)
    a = p.parse_args()
    password = os.environ["ZABBIX_ADMIN_PASSWORD"]

    token, used = login(a.url, password)
    admin = call(a.url, "user.get", {"filter": {"username": "Admin"}, "output": ["userid"]}, token)[0]
    if used != password:
        call(a.url, "user.update", {"userid": admin["userid"], "current_passwd": used, "passwd": password}, token)
        token, _ = login(a.url, password)
        changed = True

    group = call(a.url, "hostgroup.get", {"filter": {"name": ["Linux servers"]}, "output": ["groupid"]}, token)[0]
    template = call(
        a.url, "template.get", {"filter": {"host": ["Linux by Zabbix agent active"]}, "output": ["templateid"]}, token
    )[0]

    name = "GenArchi : auto-enregistrement"
    if not call(a.url, "action.get", {"filter": {"name": name}, "output": ["actionid"]}, token):
        call(
            a.url,
            "action.create",
            {
                "name": name,
                "eventsource": 2,
                "filter": {"evaltype": 0, "conditions": [{"conditiontype": 24, "operator": 2, "value": "genarchi"}]},
                "operations": [
                    {"operationtype": 2},
                    {"operationtype": 4, "opgroup": [{"groupid": group["groupid"]}]},
                    {"operationtype": 6, "optemplate": [{"templateid": template["templateid"]}]},
                ],
            },
            token,
        )
        changed = True

    # Scénario web porté par l'hôte du serveur Zabbix lui-même.
    server = call(a.url, "host.get", {"filter": {"host": ["Zabbix server"]}, "output": ["hostid"]}, token)
    scenario = "GenArchi : URL publique"
    if server and not call(a.url, "httptest.get", {"filter": {"name": scenario}, "output": ["httptestid"]}, token):
        call(
            a.url,
            "httptest.create",
            {
                "name": scenario,
                "hostid": server[0]["hostid"],
                "delay": "1m",
                "retries": 2,
                "steps": [{"name": "readyz", "url": a.public_url, "status_codes": "200", "no": 1}],
            },
            token,
        )
        changed = True

    if a.discord_webhook:
        media = call(a.url, "mediatype.get", {"filter": {"name": "Discord"}, "output": ["mediatypeid", "status"]}, token)
        if media:
            mid = media[0]["mediatypeid"]
            if media[0]["status"] != "0":
                call(a.url, "mediatype.update", {"mediatypeid": mid, "status": 0}, token)
                changed = True
            user = call(a.url, "user.get", {"userids": admin["userid"], "selectMedias": "extend"}, token)[0]
            if not any(m["mediatypeid"] == mid and m["sendto"] == a.discord_webhook for m in user["medias"]):
                medias = [m for m in user["medias"] if m["mediatypeid"] != mid]
                medias = [{k: m[k] for k in ("mediatypeid", "sendto", "active", "severity", "period")} for m in medias]
                medias.append(
                    {"mediatypeid": mid, "sendto": a.discord_webhook, "active": 0, "severity": 60, "period": "1-7,00:00-24:00"}
                )
                call(a.url, "user.update", {"userid": admin["userid"], "medias": medias}, token)
                changed = True
        action = call(
            a.url,
            "action.get",
            {"filter": {"name": "Report problems to Zabbix administrators"}, "output": ["actionid", "status"]},
            token,
        )
        if action and action[0]["status"] != "0":
            call(a.url, "action.update", {"actionid": action[0]["actionid"], "status": 0}, token)
            changed = True

    print("changed" if changed else "ok")


if __name__ == "__main__":
    main()
