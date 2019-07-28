import sys

if sys.version_info.major == 2:
  # import pip main
  try:
    from pip import main as pipmain
  except:
    from pip._internal import main as pipmain
  pip_install = lambda module: pipmain(['install',module])

else:
  import slicer
  pip_install = slicer.util.pip_install

# install requests
try:
  import requests
except:
  pip_install('requests')
  import requests
  pass

# install requests_toolbelt
try:
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
except:
  pip_install('requests_toolbelt')
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
  pass

# install OpenSSL
try:
  import OpenSSL
except:
  pip_install('pyOpenSSL')
  import OpenSSL
  pass
