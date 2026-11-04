# Secrets générés une fois et stockés dans l'état OpenTofu (bucket GCS, accès restreint à l'équipe).
# Ansible les reçoit via l'inventaire généré (fichier 0600, ignoré par git) et les écrit dans des fichiers 0600.
resource "random_password" "secret" {
  for_each = toset([
    "postgres", "replicator", "rewind", "app_db", "barman", "streaming_barman",
    "rabbitmq_app", "rabbitmq_admin", "erlang_cookie", "admin_token", "staff_token",
    "zabbix_db", "zabbix_admin",
  ])
  length  = 32
  special = false
}
