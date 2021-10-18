import pathlib, stat, shutil, urllib.request, subprocess, getpass, time, tempfile
import secrets, json, re
import IPython.utils.io
import pyngrok.ngrok, pyngrok.conf
import apt, apt.debfile
import ipywidgets


##########################/APT###################################
class _NoteProgress(apt.progress.base.InstallProgress, apt.progress.base.AcquireProgress, apt.progress.base.OpProgress):
  def __init__(self):
    apt.progress.base.InstallProgress.__init__(self)
    self._label = ipywidgets.Label()
    display(self._label)
    self._float_progress = ipywidgets.FloatProgress(min = 0.0, max = 1.0, layout = {'border':'1px solid #118800'})
    display(self._float_progress)

  def close(self):
    self._float_progress.close()
    self._label.close()

  def fetch(self, item):
    self._label.value = "fetch: " + item.shortdesc

  def pulse(self, owner):
    self._float_progress.value = self.current_items / self.total_items
    return True

  def status_change(self, pkg, percent, status):
    self._label.value = "%s: %s" % (pkg, status)
    self._float_progress.value = percent / 100.0

  def update(self, percent=None):
    self._float_progress.value = self.percent / 100.0
    self._label.value = self.op + ": " + self.subop

  def done(self, item=None):
    pass

class _MyApt:
  def __init__(self):
    self._progress = _NoteProgress()
    self._cache = apt.Cache(self._progress)

  def close(self):
    self._cache.close()
    self._cache = None
    self._progress.close()
    self._progress = None

  def update_upgrade(self):
    self._cache.update()
    self._cache.open(None)
    self._cache.upgrade()

  def commit(self):
    self._cache.commit(self._progress, self._progress)
    self._cache.clear()

  def installPkg(self, *args):
    for name in args:
      pkg = self._cache[name]
      if pkg.is_installed:
        print(f"{name} is already installed")
      else:
        print(f"Install {name}")
        pkg.mark_install()

  def installDebPackage(self, name):
    apt.debfile.DebPackage(name, self._cache).install()

  def deleteInstalledPkg(self, *args):
    for pkg in self._cache:
      if pkg.is_installed:
        for name in args:
          if pkg.name.startswith(name):
            #print(f"Delete {pkg.name}")
            pkg.mark_delete()
##########################/APT###################################



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
  ret = subprocess.run(
                ["ssh-keygen", "-lvf", "/etc/ssh/ssh_host_ed25519_key.pub"],
                stdout = subprocess.PIPE,
                check = True,
                universal_newlines = True)

  root_password = "colab"
  user_password = "colab"
  user_name = "colab"

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

