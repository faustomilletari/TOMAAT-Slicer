# import pip main
try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain

# install requests
try:
  import requests
except:
  pipmain(['install','requests'])
  import requests
  pass

# install requests_toolbelt
try:
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
except:
  pipmain(['install', 'requests_toolbelt'])
  from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
  pass
