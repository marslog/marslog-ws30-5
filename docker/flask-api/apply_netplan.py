from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/api/change-network", methods=["POST"])
def change_network():
    data = request.json
    ip = data.get("ip")
    subnet = data.get("subnet")
    gateway = data.get("gateway")
    dns = data.get("dns")

    if not ip or not subnet or not gateway or not dns:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    netplan_yaml = f'''
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses: [{ip}{subnet}]
      gateway4: {gateway}
      nameservers:
        addresses: [{dns}]
'''

    try:
        with open("/etc/netplan/01-netcfg.yaml", "w") as f:
            f.write(netplan_yaml)
        subprocess.run(["netplan", "apply"], check=True)
        return jsonify({"success": True, "new_ip": ip})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)