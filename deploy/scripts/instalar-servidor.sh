#!/usr/bin/env bash
# Prepara un servidor Ubuntu 22.04 / 24.04 NUEVO: Docker, firewall, actualizaciones automáticas, zona horaria y swap.
# Se ejecuta UNA vez, como un usuario con sudo:
#   curl -fsSL https://raw.githubusercontent.com/TU_USUARIO/DUBSS-GESTION-DEPORTIVA/main/deploy/scripts/instalar-servidor.sh | bash
#   (o, si ya clonaste el repositorio:  bash deploy/scripts/instalar-servidor.sh)
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi
USUARIO="${SUDO_USER:-$USER}"

echo "== 1/6 Actualizando el sistema =="
$SUDO apt-get update -y
$SUDO DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "== 2/6 Docker =="
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | $SUDO sh
fi
$SUDO usermod -aG docker "$USUARIO"

echo "== 3/6 Firewall (solo SSH, HTTP y HTTPS) =="
$SUDO apt-get install -y ufw
$SUDO ufw default deny incoming
$SUDO ufw default allow outgoing
$SUDO ufw allow OpenSSH
$SUDO ufw allow 80/tcp
$SUDO ufw allow 443/tcp
$SUDO ufw allow 443/udp
$SUDO ufw --force enable

echo "== 4/6 Actualizaciones de seguridad automáticas =="
$SUDO apt-get install -y unattended-upgrades git openssl
echo 'APT::Periodic::Update-Package-Lists "1"; APT::Periodic::Unattended-Upgrade "1";' | $SUDO tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null

echo "== 5/6 Zona horaria de Bolivia =="
$SUDO timedatectl set-timezone America/La_Paz

echo "== 6/6 Memoria de respaldo (swap de 2 GB) =="
if ! swapon --show | grep -q .; then
    $SUDO fallocate -l 2G /swapfile
    $SUDO chmod 600 /swapfile
    $SUDO mkswap /swapfile >/dev/null
    $SUDO swapon /swapfile
    echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab >/dev/null
    echo "vm.swappiness=10" | $SUDO tee /etc/sysctl.d/99-swap.conf >/dev/null
    $SUDO sysctl -p /etc/sysctl.d/99-swap.conf >/dev/null
fi

echo
echo "Servidor listo. CIERRA la sesión y vuelve a entrar (para que el usuario '$USUARIO' use Docker sin sudo)."
echo "Después:  git clone https://github.com/TU_USUARIO/DUBSS-GESTION-DEPORTIVA.git && cd DUBSS-GESTION-DEPORTIVA/deploy"
