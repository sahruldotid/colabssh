import pathlib, stat, shutil, urllib.request, subprocess, getpass, time, tempfile
import secrets, json, re
import IPython.utils.io
import pyngrok.ngrok, pyngrok.conf
from _MyApt import _MyApt

def _setupSSHDImpl(ngrok_token, ngrok_region):
  my_apt = _MyApt()
  my_apt.commit()
  subprocess.run(["unminimize"], input = "y\n", check = True, universal_newlines = True)
  my_apt.installPkg("openssh-server")
  my_apt.commit()
  my_apt.close()

  #Reset host keys
  for i in pathlib.Path("/etc/ssh").glob("ssh_host_*_key"):
    i.unlink()
  subprocess.run(
                  ["ssh-keygen", "-A"],
                  check = True)

  #Prevent ssh session disconnection.
  with open("/etc/ssh/sshd_config", "a") as f:
    f.write("\n\n# Options added by remocolab\n")
    f.write("ClientAliveInterval 120\n")
   

  msg = ""
  msg += "ED25519 key fingerprint of host:\n"
  ret = subprocess.run(
                ["ssh-keygen", "-lvf", "/etc/ssh/ssh_host_ed25519_key.pub"],
                stdout = subprocess.PIPE,
                check = True,
                universal_newlines = True)
  msg += ret.stdout + "\n"

  root_password = "colab"
  user_password = "colab"
  user_name = "colab"
  msg += "✂️"*24 + "\n"
  msg += f"root password: {root_password}\n"
  msg += f"{user_name} password: {user_password}\n"
  msg += "✂️"*24 + "\n"
  subprocess.run(["useradd", "-s", "/bin/bash", "-m", user_name])
  subprocess.run(["adduser", user_name, "sudo"], check = True)
  subprocess.run(["chpasswd"], input = f"root:{root_password}", universal_newlines = True)
  subprocess.run(["chpasswd"], input = f"{user_name}:{user_password}", universal_newlines = True)
  subprocess.run(["service", "ssh", "restart"])

  ssh_common_options =  "-o UserKnownHostsFile=/dev/null -o VisualHostKey=yes"

  # Setting up ngrok
  pyngrok_config = pyngrok.conf.PyngrokConfig(auth_token = ngrok_token, region = ngrok_region)
  ssh_tunnel = pyngrok.ngrok.connect(addr = 22, proto = "tcp", pyngrok_config = pyngrok_config)
  m = re.match("tcp://(.+):(\d+)", ssh_tunnel.public_url)
  hostname = m.group(1)
  port = m.group(2)
  ssh_common_options += f" -p {port}"
  

  msg += "---\n"
  msg += "Command to connect to the ssh server:\n"
  msg += "✂️"*24 + "\n"
  msg += f"ssh {ssh_common_options} {user_name}@{hostname}\n"
  msg += "✂️"*24 + "\n"
  return msg

def _setupSSHDMain(ngrok_region, ngrok_token):
  if not ngrok_region:
    print("Select your ngrok region:")
    print("us - United States (Ohio)")
    print("eu - Europe (Frankfurt)")
    print("ap - Asia/Pacific (Singapore)")
    print("au - Australia (Sydney)")
    print("sa - South America (Sao Paulo)")
    print("jp - Japan (Tokyo)")
    print("in - India (Mumbai)")
    ngrok_region = input()

  if not ngrok_token:
    print("Insert ngrok auth_token")
    ngrok_token = input()

  return (True, _setupSSHDImpl(ngrok_token, ngrok_region))

def setupSSHD(ngrok_region = None, ngrok_token = None):
  s, msg = _setupSSHDMain(ngrok_region, ngrok_token)
  print(msg)

