# TOMAAT-slicer
TOMAAT-slicer: access deep learning modules over the cloud using [3D Slicer](https://www.slicer.org).
This project is a Slicer extension that allows you to run perform deep learning based segmentation of medical volumes through inference service deployed on the cloud via [TOMAAT](https://github.com/faustomilletari/TOMAAT)

## Disclaimer
This software is provided "as-it-is" without any guarantee of correct functionality or guarantee of quality. No formal support for this software will be given to users. This slicer extension and any other part of the TOMAAT project should not be used for medical purposes. In particular this software should not be used to make, support, gain evidence on and aid medical decisions, interventions or diagnoses. Any use of this software for finalities other than "having fun with it" is prohibited.
Moreover, this slicer extension will give you the possibility of running inference on remotely deployed deep learning services by sending your data over the network to remote hosts without any encription. The privacy of the data is not guardanteed and TOMAAT should not be held responsible for data mis-use following transfer. Although we reccommend remote hosts providing inference not to store or hold any data that they get through TOMAAT-slicer, we cannot guardantee that any data you transfer to a remote inference service is not going to be misused, stored or manipulated. Use TOMAAT-slicer and TOMAAT responsibly.

## Architecture
In this repository you find TOMAAT-slicer. TOMAAT-slicer is written in python and contains three main parts. One is the GUI, which allows user interaction directly from 3D-Slicer. The second is the "Service discovery" logic and the third is the "Segmentation" logic.

### GUI

Our gui is divided in multiple parts using collapsible buttons. It is written in PythonQt and is following the format suggested by 3D-Slicer extension wizard.

* Info: contains the logo of our extension
* Direct Connection: allows you to directly specify the URL of a TOMAAT service residing on another host connect via network in order to use it for inference. This is useful to people who want to run inference on their own machine without making their service available to anyone else who doesn't know the address of the enpoint.
* Public Server List: Allows to specify the URL of a public server list discovery service (default http://tomaat.cloud:8000/discovery) and obtian a list of available services that are present on the network and can be distributed anywhere in the world. The user can select the service that is appropriate for the type of data at hand, if present, and submit volumes to it. 
Service discovery happens when the user clicks on the button 'Discover Services'
* Segmentation: allows to select a volume from the MRML scene in 3D-Slicer and send it for inference to the remote host selected either in the Direct Connection pane or the Public Server List pane. By adjusting the threshold level it will be possible to threshold the probability maps obtained via deep learning from the remote host using different confidence values.
Segemntation happens when the user clicks on the button 'Segment'.


### Architecture
A summary of the current architecture of TOMAAT is shown below:
![architecture](http://tomaat.cloud/images/architecture.jpg)
All communications between local and remote machines -- for service discovery and inference -- happen through HTTP protocol. Services are discovered by a GET request to the appropriate URL while images are segmented through a POST request containing JSON data.
The interfaces used for communication are specified in the following:

### Service discovery interface
After the GET request is made to the service discovery server url (for example http://tomaat.cloud:8000/discovery) a JSON message is received. It contains:
* 'hosts': list of URL of inference services (endpoints)
* 'modalities': list of modalities the endpoints are capable of processing
* 'anatomies': list of anatomies the endpoints are capable of segmenting
* 'descriptions': list of endpoint descriptions (which method is used, which resolution, how fast it is etc...)

### Segmentation service interface
Segmentation happens by first dumping to disk the selected volume in a temporary folder in MHA format. At this point the volume will be re-read back into the TOMAAT-slicer extension and processed into a string through 'base64.encodestring'. At this point a JSON message will be created with the following fields:
* 'content_mha': string containing the data from the MHA file
* 'threshold': threshold to apply to the final segmentation result
* 'module_version': the version of the TOMAAT-slicer extension
