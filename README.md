# TOMAAT-slicer
TOMAAT-slicer is a Slicer extension that allows you to run perform deep learning based segmentation of medical volumes through inference service deployed on the cloud

## Disclaimer
This software is provided "as-it-is" without any guarantee of correct functionality or guarantee of quality. No formal support for this software will be given to users. This slicer extension and any other part of the TOMAAT project should not be used for medical purposes. In particular this software should not be used to make, support, gain evidence on and aid medical decisions, interventions or diagnoses. Any use of this software for finalities other than "having fun with it" is prohibited.
Moreover, this slicer extension will give you the possibility of running inference on remotely deployed deep learning services by sending your data over the network to remote hosts without any encription. The privacy of the data is not guardanteed and TOMAAT should not be held responsible for data mis-use following transfer. Although we reccommend remote hosts providing inference not to store or hold any data that they get through TOMAAT-slicer, we cannot guardantee that any data you transfer to a remote inference service is not going to be misused, stored or manipulated. Use TOMAAT-slicer and TOMAAT responsibly.

## Architecture
In this repository you find TOMAAT-slicer. TOMAAT-slicer is written in python and contains three main parts. One is the GUI, which allows user interaction directly from 3D-Slicer. The second is the "Service discovery" logic and the third is the "Segmentation" logic.

### GUI

Our gui is divided in multiple parts using collapsible buttons. It is written in PyQt and is following the format suggested by slicer extension wizard.

* Info: contains the logo of our extension
* Direct Connection: allows you to directly specify the URL of a TOMAAT service residing on another host connect via network in order to use it for inference. This is useful to people who want to run inference on their own machine without making their service available to anyone else who doesn't know the address of the enpoint.
* Public Server List: Allows to specify the URL of a public server list discovery service (default http://tomaat.cloud:8000/discovery) and obtian a list of available services that are present on the network and can be distributed anywhere in the world. The user can select the service that is appropriate for the type of data at hand, if present, and submit volumes to it. 
Service discovery happens when the user clicks on the button 'Discover Services'
* Segmentation: allows to select a volume from the MRML scene in 3D-Slicer and send it for inference to the remote host selected either in the Direct Connection pane or the Public Server List pane. By adjusting the threshold level it will be possible to threshold the probability maps obtained via deep learning from the remote host using different confidence values.
Segemntation happens when the user clicks on the button 'Segment'.


### Architecture
A summary of the current architecture of TOMAAT is shown below:
![architecture](http://tomaat.cloud/images/architecture.png)


