#!/usr/bin/env python3
"""
破晓 Daybreak 一键启动/重启脚本
用法: python3 start_daybreak.py [up|down|restart|status]
"""
import subprocess, sys, time, requests, json

BASE = "http://127.0.0.1:8000"
COMPOSE_FILE = "docker/docker-compose.yml"
PROJECT_DIR = "/home/AI/Z3r0"

def run(cmd):
    print(f"  $ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip():
        print(f"  stderr: {r.stderr.strip()}")
    return r.returncode == 0

def get_token():
    try:
        r = requests.post(f"{BASE}/api/system-users/login",
                          json={"email": "admin@daybreak.local", "password": "admin"}, timeout=5)
        data = r.json()
        td = data.get("data", {})
        return td.get("access_token") or td.get("token")
    except:
        return None

def ensure_sandbox():
    token = get_token()
    if not token:
        print("  Cannot get token, skipping sandbox check")
        return
    headers = {"X-Daybreak-Access-Token": token}

    # Check available containers
    r = requests.get(f"{BASE}/api/sandbox-containers/available", headers=headers, timeout=5)
    avs = r.json().get("data", {}).get("items", [])
    if avs:
        print(f"  Sandbox OK: {avs[0]['container_name']} (running)")
        return

    # Check if any container exists but not running
    r = requests.get(f"{BASE}/api/sandbox-containers", headers=headers, timeout=5)
    cts = r.json().get("data", {}).get("items", [])
    if cts:
        # Try to start existing container
        ct = cts[0]
        print(f"  Container {ct['container_name']} status={ct['status']}, attempting start...")
        # Start via docker directly
        run(f"docker start {ct['container_name']}")
        # Set restart policy
        run(f"docker update --restart=always {ct['container_name']}")
        time.sleep(2)
        return

    # No container exists, create one
    print("  No sandbox container found, creating...")
    # Check if sandbox-runtime image is registered
    r = requests.get(f"{BASE}/api/sandbox-images", headers=headers, timeout=5)
    imgs = r.json().get("data", {}).get("items", [])
    if not imgs:
        print("  Registering sandbox-runtime:latest image...")
        requests.post(f"{BASE}/api/sandbox-images", headers=headers,
                      json={"image_name": "sandbox-runtime:latest", "control_proxy_port": 8000}, timeout=10)

    # Get host info
    r = requests.get(f"{BASE}/api/hosts", headers=headers, timeout=5)
    hosts = r.json().get("data", {}).get("items", [])
    if not hosts:
        print("  ERROR: No Docker host registered")
        return

    host = hosts[0]
    img = imgs[0] if imgs else None
    if not img:
        print("  ERROR: No sandbox image available")
        return

    # Create container
    print(f"  Creating sandbox container on host {host['ip_address']}...")
    r = requests.post(f"{BASE}/api/sandbox-containers", headers=headers,
                      json={"host_id": host["id"], "image_id": img["id"]}, timeout=30)
    ct_data = r.json()
    if ct_data.get("code") == 200:
        ct_name = ct_data["data"].get("container_name", "unknown")
        print(f"  Created: {ct_name}")
        # Set restart policy
        run(f"docker update --restart=always {ct_name}")
    else:
        print(f"  Create failed: {ct_data.get('message', 'unknown')}")

def cmd_up():
    print("\n[1/3] Starting Docker Compose services...")
    run(f"cd {PROJECT_DIR} && docker compose -f {COMPOSE_FILE} up -d")

    print("\n[2/3] Waiting for app to be ready...")
    for i in range(30):
        try:
            r = requests.get(f"{BASE}/openapi.json", timeout=2)
            if r.status_code == 200:
                print(f"  App is ready! (took ~{(i+1)*2}s)")
                break
        except:
            pass
        time.sleep(2)
    else:
        print("  WARNING: App may not be ready yet")

    print("\n[3/3] Ensuring sandbox container...")
    ensure_sandbox()

    print("\n" + "="*50)
    print("  破晓 Daybreak 已启动!")
    print(f"  访问: http://127.0.0.1:8000")
    print("  账号: admin@daybreak.local / admin")
    print("="*50)

def cmd_down():
    print("\nStopping Daybreak...")
    run(f"cd {PROJECT_DIR} && docker compose -f {COMPOSE_FILE} down")
    # Also stop sandbox containers (they're outside compose)
    run("docker ps --filter name=sandbox-runtime --format '{{.Names}}' | xargs -r docker stop")
    print("  Daybreak stopped.")

def cmd_restart():
    cmd_down()
    time.sleep(3)
    cmd_up()

def cmd_status():
    print("\nDaybreak Status:")
    print("-" * 40)

    # Docker containers
    run("docker ps --filter name=daybreak --filter name=sandbox-runtime --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

    # App health
    try:
        r = requests.get(f"{BASE}/openapi.json", timeout=3)
        print(f"\n  App API: {'OK' if r.status_code == 200 else 'ERROR'}")
    except:
        print("\n  App API: NOT REACHABLE")

    # Login test
    token = get_token()
    print(f"  Login:   {'OK' if token else 'FAILED'}")

    if token:
        headers = {"X-Daybreak-Access-Token": token}
        r = requests.get(f"{BASE}/api/sandbox-containers/available", headers=headers, timeout=5)
        avs = r.json().get("data", {}).get("items", [])
        print(f"  Sandbox: {len(avs)} container(s) available")
        for av in avs:
            print(f"    - {av['container_name']} ({av['status']})")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "up"

    if action == "up":
        cmd_up()
    elif action == "down":
        cmd_down()
    elif action == "restart":
        cmd_restart()
    elif action == "status":
        cmd_status()
    else:
        print(f"Usage: python3 {sys.argv[0]} [up|down|restart|status]")
