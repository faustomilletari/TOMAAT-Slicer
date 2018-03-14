try:
  import requests
except:
  import pip
  pip.main(['install','requests'])
  import requests
  pass

try:
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
except:
  import pip
  pip.main(['install', 'requests_toolbelt'])
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
  pass