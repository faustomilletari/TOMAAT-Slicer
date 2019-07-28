from utils import dependencies as tomaatdependencies

import base64
import logging
import os
import tempfile
import uuid

import ctk
import qt
import requests
import slicer
import json
import sys
import numpy as np

from qt import QTimer

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from slicer.ScriptedLoadableModule import *

from utils.ui import ScalarVolumeWidget, MarkupsFiducialWidget, TransformWidget, SliderWidget, CheckboxWidget, \
    RadioButtonWidget
from utils.ui import collapsible_button, add_image, add_textbox, add_button, add_label
from utils.tls import SSLUtil

MODULE_VERSION = 'Slicer-v2'

#
# TOMAAT
#

CONTRIB = ["Fausto Milletari"]
MESSAGE = \
    """
      This module performs analysis of volumetric medical data using 3D convolutional neural 
      networks. It is intended as a proof of concept and a research module only.
      The computation of the results is offloaded to remote host. 
      You need a fast connection to obtain satisfactory results. 
      In no way the results provided by this model should be trusted to make any clinical judgement. 
      This module is provided without any guarantee about its functionality, precision and correctness of the results.
      This module works by exchanging data (medical images) over the network. 
      There is no guarantee about the destiny of data sent through this model to any remote host. 
      Normally data gets processed and then deleted but this cannot be formally guaranteed. 
      Also, no guarantees about privacy can be made. 
      You are responsible for the anonimization of the data you use to run inference. 
    """


class ServiceEntry(qt.QTreeWidgetItem):
    endpoint_data = None


#
# TOMAAT
#

class TOMAAT(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "TOMAAT"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = CONTRIB
        self.parent.helpText = MESSAGE
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = "None"


#
# TOMAATWidget
#

class TOMAATWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.predictionUrl = ''
        self.interfaceUrl = ''
        self.clearToSendMsg = False
        # Instantiate and connect widgets ...

        #
        # LOGO area
        #
        logoCollapsibleButton = collapsible_button('Info')

        self.layout.addWidget(logoCollapsibleButton)
        self.logolayout = qt.QFormLayout(logoCollapsibleButton)

        self.logolabel, _ = \
            add_image(os.path.join(os.path.split(os.path.realpath(__file__))[0], "Resources/Icons/TOMAAT_INFO.png"))

        self.logolayout.addRow(self.logolabel)

        #
        # Direct Connection area
        #
        directConnectionCollapsibleButton = collapsible_button('Direct Connection')
        self.layout.addWidget(directConnectionCollapsibleButton)
        self.directConnectionLayout = qt.QFormLayout(directConnectionCollapsibleButton)

        self.urlBoxDirectConnection = add_textbox("https://localhost:9000")

        self.urlBoxButton = add_button(
            text='Confirm', tooltip_text='Confirm entry', click_function=self.select_from_textbox, enabled=True
        )

        self.directConnectionLayout.addRow("Server URL: ", self.urlBoxDirectConnection)

        self.directConnectionLayout.addRow(self.urlBoxButton)

        directConnectionCollapsibleButton.collapsed = True

        #
        # Managed Connection area
        #
        managedConenctionCollapsibleButton = collapsible_button('Public Server List')
        self.layout.addWidget(managedConenctionCollapsibleButton)

        self.managedConnectionLayout = qt.QFormLayout(managedConenctionCollapsibleButton)

        self.urlBoxManagedConnection = add_textbox("http://tomaat.cloud:8001/discover")

        self.managedConnectionLayout.addRow("Discovery Server URL: ", self.urlBoxManagedConnection)

        self.serviceTree = qt.QTreeWidget()
        self.serviceTree.setHeaderLabel('Available services')
        self.serviceTree.itemSelectionChanged.connect(self.select_from_tree)

        self.discoverServicesButton = add_button(
            "Discover Services",
            "Discover available segmentation services on the net.",
            self.onDiscoverButton,
            True
        )

        self.serviceDescription = add_label('')

        self.managedConnectionLayout.addRow(self.discoverServicesButton)

        self.managedConnectionLayout.addRow(self.serviceTree)

        self.managedConnectionLayout.addRow(self.serviceDescription)

        self.processingCollapsibleButton = None

    def cleanup(self):
        pass

    def add_widgets(self, instructions):
        if self.processingCollapsibleButton is not None:
            self.processingCollapsibleButton.deleteLater()
        self.processingCollapsibleButton = ctk.ctkCollapsibleButton()
        self.processingCollapsibleButton.text = "Processing"
        self.layout.addWidget(self.processingCollapsibleButton)

        self.processingFormLayout = qt.QFormLayout(self.processingCollapsibleButton)

        # Add vertical spacer
        self.layout.addStretch(1)

        self.widgets = []

        for instruction in instructions:
            if instruction['type'] == 'volume':
                volume = ScalarVolumeWidget(destination=instruction['destination'])
                self.widgets.append(volume)
                self.processingFormLayout.addRow('{} Volume: '.format(instruction['destination']), volume)

            if instruction['type'] == 'fiducials':
                fiducial = MarkupsFiducialWidget(destination=instruction['destination'])
                self.widgets.append(fiducial)
                self.processingFormLayout.addRow('{} Fiducials: '.format(instruction['destination']), fiducial)

            if instruction['type'] == 'transform':
                transform = TransformWidget(destination=instruction['destination'])
                self.widgets.append(transform)
                self.processingFormLayout.addRow('{} Transform: '.format(instruction['destination']), transform)

            if instruction['type'] == 'slider':
                slider = SliderWidget(
                    destination=instruction['destination'],
                    minimum=instruction['minimum'],
                    maximum=instruction['maximum']
                )
                self.widgets.append(slider)
                self.processingFormLayout.addRow('{} Slider: '.format(instruction['destination']), slider)

            if instruction['type'] == 'checkbox':
                checkbox = CheckboxWidget(
                    destination=instruction['destination'],
                    text=instruction['text']
                )
                self.widgets.append(checkbox)
                self.processingFormLayout.addRow('{} Checkbox: '.format(instruction['destination']), checkbox)

            if instruction['type'] == 'radiobutton':
                radiobox = RadioButtonWidget(
                    destination=instruction['destination'],
                    options=instruction['options']
                )
                self.widgets.append(radiobox)
                self.processingFormLayout.addRow('{} Options: '.format(instruction['text']), radiobox)

        self.applyButton = add_button('Process', 'Run the algorithm', enabled=True)

        self.processingFormLayout.addRow(self.applyButton)

        # connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)

    def select_from_textbox(self):
        print('USING HOST IN DIRECT CONNECTION PANE')
        self.predictionUrl = self.urlBoxDirectConnection.text + '/predict'
        self.interfaceUrl = self.urlBoxDirectConnection.text + '/interface'
        self.serviceDescription.setText('')

        logic = InterfaceDiscoveryLogic()

        if not self.checkConnection(self.interfaceUrl):
            return

        try:
            interface_specification = logic.run(self.interfaceUrl)
            self.add_widgets(interface_specification)
        except:
            slicer.util.messageBox("Error during interface discovery")
            return

    def select_from_tree(self):
        item = self.serviceTree.selectedItems()
        item = item[0]

        if isinstance(item, ServiceEntry):
            self.predictionUrl = item.endpoint_data['prediction_url']
            self.interfaceUrl = item.endpoint_data['interface_url']
            self.serviceDescription.setText(item.endpoint_data['description'])

        logic = InterfaceDiscoveryLogic()

        if not self.checkConnection(self.interfaceUrl):
            return

        try:
            interface_specification = logic.run(self.interfaceUrl)
            self.add_widgets(interface_specification)
        except:
            slicer.util.messageBox(
                "The element you selected is not a service, or there was an error during interface discovery")

    def onDiscoverButton(self):
        logic = ServiceDiscoveryLogic()

        self.serviceTree.clear()

        try:
            data = logic.run(self.urlBoxManagedConnection.text)
        except:
            slicer.util.messageBox("Error during service discovery")
            return

        for modality in list(data.keys()):
            mod_item = qt.QTreeWidgetItem()
            mod_item.setText(0, 'Modality: ' + str(modality))

            self.serviceTree.addTopLevelItem(mod_item)

            for anatomy in list(data[modality].keys()):
                anatom_item = qt.QTreeWidgetItem()
                anatom_item.setText(0, 'Anatomy: ' + str(anatomy))

                mod_item.addChild(anatom_item)

                for task in list(data[modality][anatomy].keys()):
                    dim_item = qt.QTreeWidgetItem()
                    dim_item.setText(0, 'Task: ' + str(task))

                    anatom_item.addChild(dim_item)

                    for entry in data[modality][anatomy][task]:
                        elem = ServiceEntry()
                        elem.setText(0, 'Service: ' + entry['name'] + '. Sid:' + entry['SID'])
                        elem.endpoint_data = entry
                        dim_item.addChild(elem)

    def onConnectDirectlyButton(self):
        for elem in self.removeListGuiReset:
            self.delete_element(elem)
        self.removeListGuiReset = []

        self.urlBoxDirectConnection = qt.QLineEdit()
        self.urlBoxDirectConnection.text = "https://localhost:9000"
        self.connectionFormLayout.addRow("Server URL: ", self.urlBoxDirectConnection)

        self.removeListGuiReset += [self.urlBoxDirectConnection]

    def onAgreeButton(self):
        self.clearToSendMsg = True

    def confirmationPopup(self, message, autoCloseMsec=1000):
        """Display an information message in a popup window for a short time.
        If autoCloseMsec>0 then the window is closed after waiting for autoCloseMsec milliseconds
        If autoCloseMsec=0 then the window is not closed until the user clicks on it.
        """
        messagePopup = qt.QDialog()
        layout = qt.QVBoxLayout()
        messagePopup.setLayout(layout)
        label = qt.QLabel(message, messagePopup)
        layout.addWidget(label)

        okButton = qt.QPushButton("Submit")
        layout.addWidget(okButton)
        okButton.connect('clicked()', self.onAgreeButton)
        okButton.connect('clicked()', messagePopup.close)

        stopButton = qt.QPushButton("Stop")
        layout.addWidget(stopButton)
        stopButton.connect('clicked()', messagePopup.close)

        messagePopup.exec_()

    def onApplyButton(self):
        logic = TOMAATLogic()

        if self.predictionUrl == '':
            logging.info('NO SERVER HAS BEEN SPECIFIED')
            return

        self.confirmationPopup(
            '<center>By clicking Submit button you acknowledge that you <br>'
            'are going to send the specified data over the internet to <br>'
            'a remote server at URL <b>{}</b>. It is your responsibility to <br>'
            'ensure that by doing so you are not violating any rules governing <br>'
            'access to the data being sent. More info '
            '<a href="https://github.com/faustomilletari/TOMAAT-Slicer/blob/master/README.md">here</a>.</center>'.format(
                self.predictionUrl)
        )

        if not self.clearToSendMsg:
            logging.info('USER REQUESTED STOP')
            return

        if not self.checkConnection(self.predictionUrl):
            logging.info('UNSAFE CONNECTION STOP')
            return

        self.clearToSendMsg = False

        print('CONNECTING TO SERVER {}'.format(self.predictionUrl))

        progress_bar = slicer.util.createProgressDialog(labelText="Uploading to remote server",
                                                        windowTitle="Uploading...")
        progress_bar.setCancelButton(0)

        try:
            logic.run(self.widgets, self.predictionUrl, progress_bar)
        except Exception as e:
            slicer.util.messageBox("Error during remote processing")

    def checkConnection(self, url):
        logic = TOMAATLogic()
        result = logic.verifyConnectionToServer(url)
        if not result["success"]:
            if "fingerprint" in result.keys():
                # untrusted host -> ask to add to keystore
                if slicer.util.confirmYesNoDisplay(
                        "{}\nDo you want to consider the following data as trusted in the future:\n{}".format(result['msg'], str(
                            result['fingerprint']))
                ):
                    host, port, fprint = result['fingerprint']
                    # write to SSLUtil
                    SSLUtil.fingerprintsLocal.update({fprint: {"port": port, "host": host}})
                    logic.writeFingerprintFile()
                    return True
                return False

            else:
                # no connection to host
                slicer.util.errorDisplay(result["msg"])
                return False
        return True


def create_callback(encoder, progress_bar):
    encoder_len = encoder.len

    def callback(monitor):
        progress_bar.value = float(monitor.bytes_read) / float(encoder_len) * 100

    return callback


#
# TOMAATLogic
#

class TOMAATLogic(ScriptedLoadableModuleLogic):
    message = {}
    savepath = tempfile.gettempdir()
    node_name = None
    fingerprint_file = os.path.join(os.path.dirname(__file__), "known_hosts.json")
    if os.path.exists(fingerprint_file):
        SSLUtil.loadFingerprintsFromFile(fingerprint_file)

    list_files_cleanup = []


    def add_scalar_volume_to_message(self, widget):
        id = uuid.uuid4()
        tmp_filename_mha = os.path.join(self.savepath, str(id) + '.mha')
        slicer.util.saveNode(widget.currentNode(), tmp_filename_mha)

        self.node_name = widget.currentNode().GetName()

        with open(tmp_filename_mha, 'rb') as voldata:
            self.message[widget.destination] = __base64_encode__(voldata.read())

        for view in ['Red', 'Green', 'Yellow']:
            view_widget = slicer.app.layoutManager().sliceWidget(view)
            view_logic = view_widget.sliceLogic()

            view_logic.GetSliceCompositeNode().SetForegroundVolumeID(widget.currentNode().GetID())
            view_logic.GetSliceCompositeNode().SetBackgroundVolumeID(widget.currentNode().GetID())

            view_logic.GetSliceCompositeNode().SetLabelOpacity(0.5)
            view_logic.FitSliceToAll()

        sliceWidget = slicer.app.layoutManager().sliceWidget('Red')
        sliceLogic = sliceWidget.sliceLogic()
        sliceNode = sliceLogic.GetSliceNode()
        sliceNode.SetSliceVisible(True)

        self.list_files_cleanup.append(tmp_filename_mha)

    def add_fiducial_list_to_message(self, widget):
        fidsl = widget.currentNode()
        coordsList = np.zeros(shape=(fidsl.GetNumberOfFiducials(),3))
        coord = [ 0., 0., 0.]
        for i in range(fidsl.GetNumberOfFiducials()):
            fidsl.GetNthFiducialPosition(i, coord)
            coordsList[i,:] = coord
        # point format: 0.243534,0.111,9584.0;0.1,0.2,0.3;...
        result = ";".join([",".join([str(c) for c in coords]) for coords in coordsList])
        self.message[widget.destination] = result

    def add_transform_to_message(self, widget):
        id = uuid.uuid4()
        dtype = {
            'grid': '.nii.gz',
            'bspline': '.h5',
            'linear': '.mat'
        }
        selected_node = widget.currentNode()

        transformType = ""
        if isinstance(selected_node, slicer.vtkMRMLGridTransformNode):
            transformType = "grid"
        elif isinstance(selected_node, slicer.vtkMRMLBSplineTransformNode):
            transformType = "bspline"
        elif isinstance(selected_node, slicer.vtkMRMLLinearTransformNode):
            transformType = "linear"

        tmp_transform = os.path.join(self.savepath, str(id) + dtype[transformType])
        slicer.util.saveNode(widget.currentNode(), tmp_transform)

        self.node_name = widget.currentNode().GetName()

        # transform encoding:
        # <filetype> newline
        # <base64 of file>

        trf_message = dtype[transformType][1:] + "\n"
        with open(tmp_transform, 'rb') as trfdata:
            trf_message += __base64_encode__(trfdata.read())

        self.message[widget.destination] = trf_message

        self.list_files_cleanup.append(tmp_transform)

    def add_slider_value_to_message(self, widget):
        self.message[widget.destination] = str(widget.value)

    def add_checkbox_value_to_message(self, widget):
        self.message[widget.destination] = str(widget.value)

    def add_radiobutton_value_to_message(self, widget):
        self.message[widget.destination] = str(widget.value)

    def receive_label_volume(self, data):
        tmp_segmentation_mha = os.path.join(self.savepath, data['label']+'_result' + '.mha')
        with open(tmp_segmentation_mha, 'wb') as f:
            f.write(__base64_decode__( data['content'] ))

        if sys.version_info.major == 2:
            # returnNode is deprecated in newer Slicer versions
            success, node = slicer.util.loadLabelVolume(tmp_segmentation_mha, properties={'show': False}, returnNode=True)
        else:
            node = slicer.util.loadLabelVolume(tmp_segmentation_mha, properties={'show': False})

        os.remove(tmp_segmentation_mha)

        logic = slicer.modules.volumerendering.logic()
        volumeNode = slicer.util.getNode(node.GetName())
        displayNode = logic.CreateVolumeRenderingDisplayNode()

        slicer.mrmlScene.AddNode(displayNode)
        displayNode.UnRegister(logic)
        logic.UpdateDisplayNodeFromVolumeNode(displayNode, volumeNode)
        volumeNode.AddAndObserveDisplayNodeID(displayNode.GetID())

        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()

        for view in ['Red', 'Green', 'Yellow']:
            view_widget = slicer.app.layoutManager().sliceWidget(view)
            view_logic = view_widget.sliceLogic()

            view_logic.GetSliceCompositeNode().SetLabelVolumeID(node.GetID())

            view_logic.GetSliceCompositeNode().SetLabelOpacity(0.5)
            view_logic.FitSliceToAll()

        sliceWidget = slicer.app.layoutManager().sliceWidget('Red')
        sliceLogic = sliceWidget.sliceLogic()
        sliceNode = sliceLogic.GetSliceNode()
        sliceNode.SetSliceVisible(True)

    def receive_vtk_mesh(self, data):
        tmp_mesh_vtk = os.path.join(self.savepath, str(uuid.uuid4()) + '_mesh' + '.vtk')
        with open(tmp_mesh_vtk, 'wb') as f:
            f.write(__base64_decode__( data['content'] ))
        slicer.util.loadModel(tmp_mesh_vtk)

        os.remove(tmp_mesh_vtk)

    def receive_fiducials(self, data):
        tmp_fiducials_fcsv = os.path.join(self.savepath, str(uuid.uuid4()) + '_fiducials' + '.fcsv')
        pointData = data
        if isinstance(pointData,bytes):
            pointData = pointData.decode("utf-8")
        prefix = """
# Markups fiducial file version = 4.9
# CoordinateSystem = 0
# columns = id,x,y,z,ow,ox,oy,oz,vis,sel,lock,label,desc,associatedNodeID"""
        with open(tmp_fiducials_fcsv, 'wb') as f:
            f.write(prefix.encode("utf-8"))
            for i,row in enumerate(data['content'].split(";")):
                x,y,z = row.split(",")
                f.write("\n{},{},{},{},0,0,0,1,1,1,0,{},,".format("Fid-ID"+str(i),x,y,z,"Fid-"+str(i+1)).encode("utf-8"))

        slicer.util.loadMarkupsFiducialList(tmp_fiducials_fcsv)

    def receive_transform(self, data, transformType):
        if not transformType in ['grid', 'bspline', 'linear']:
            print("Unknown transform type! Skip data entry.")
            return
        dtype = {
            'grid': '.nii.gz',
            'bspline': '.h5',
            'linear': '.mat'
        }
        tmp_transform = os.path.join(self.savepath, self.node_name + '_result' + dtype[transformType])
        with open(tmp_transform, 'wb') as f:
            f.write(__base64_decode__( data['content'] ))

        if sys.version_info.major == 2:
            # returnNode is deprecated in newer Slicer versions
            success, node = slicer.util.loadTransform(tmp_transform, returnNode=True)
        else:
            node = slicer.util.loadTransform(tmp_transform)

        os.remove(tmp_transform)

    def receive_plain_text(self, data):
        slicer.util.messageBox(data['content'], windowTitle=data['label'])

    def receive_delayed_response(self, data, server_url):
        timer = QTimer()

        delayed_url = server_url.replace('/predict', '/responses')

        def check_response():
            print('TRYING TO OBTAIN DELAYED RESPONSE')
            reply = SSLUtil.post(delayed_url, data={'request_id': data['request_id']}, timeout=5.0)
            responses_json = reply.json()
            self.process_responses(responses_json, server_url)

        timer.singleShot(1000, check_response)

    def process_responses(self, responses_json, server_url):
        for response in responses_json:
            if response['type'] == 'LabelVolume':
                self.receive_label_volume(response)

            if response['type'] == 'VTKMesh':
                self.receive_vtk_mesh(response)

            if response['type'] == 'Fiducials':
                self.receive_fiducials(response)

            if response['type'] == 'TransformGrid':
                self.receive_transform(response, transformType='grid')

            if response['type'] == 'TransformBSpline':
                self.receive_transform(response, transformType='bspline')

            if response['type'] == 'TransformLinear':
                self.receive_transform(response, transformType='linear')

            if response['type'] == 'PlainText':
                self.receive_plain_text(response)

            if response['type'] == 'DelayedResponse':
                self.receive_delayed_response(response, server_url)

        self.cleanup()

    def run(self, widgets, server_url, progress_bar):
        logging.info('Processing started')

        for widget in widgets:
            if widget.type == 'ScalarVolumeWidget':
                self.add_scalar_volume_to_message(widget)

            if widget.type == 'MarkupsFiducialWidget':
                self.add_fiducial_list_to_message(widget)

            if widget.type == 'TransformWidget':
                self.add_transform_to_message(widget)

            if widget.type == 'SliderWidget':
                self.add_slider_value_to_message(widget)

            if widget.type == 'CheckboxWidget':
                self.add_checkbox_value_to_message(widget)

            if widget.type == 'RadioButtonWidget':
                self.add_radiobutton_value_to_message(widget)

        self.message['module_version'] = MODULE_VERSION

        encoder = MultipartEncoder(self.message)
        progress_bar.open()
        callback = create_callback(encoder, progress_bar)

        monitor = MultipartEncoderMonitor(encoder, callback)

        reply = SSLUtil.post(server_url, data=monitor, headers={'Content-Type': monitor.content_type})

        print('MESSAGE SENT')

        responses_json = reply.json()

        print('RESPONSE RECEIVED')

        self.process_responses(responses_json, server_url)

        print('DONE')

        return

    def cleanup(self):
        for file in self.list_files_cleanup:
            if os.path.isfile(file):
                os.remove(file)
        self.list_files_cleanup = []

    def verifyConnectionToServer(self, server_url):
        if sys.version_info.major == 2:
            from urlparse import urlparse
        else:
            from urllib.parse import urlparse
        res = urlparse(server_url)
        if res.scheme != "https":
            return {"success": False, "msg": "No HTTPS connection!"}

        # try to connect to interface
        url = "https://" + str(res.hostname)
        if res.port:
            url += ":" + str(res.port)
        url += "/interface"

        success_safe = True
        success_unsafe = True
        # test verified connection
        try:
            SSLUtil.get(url)
        except:
            success_safe = False

        if not success_safe:
            # test unverified connection
            try:
                SSLUtil.get(url, allow_mitm=True)
            except:
                success_unsafe = False

        if success_safe and success_unsafe:
            return {"success": True, "msg": "Connection successful!"}
        if success_unsafe and not success_safe:
            # No trusted connection
            fp = SSLUtil.requestFingerprintFromURL(url)
            return {"success": False, "msg": "Untrusted connection! The request was cancelled!", "fingerprint": fp}
        if not success_unsafe:
            return {"success": False, "msg": "Host is not reachable! ({})".format(url)}

    def writeFingerprintFile(self):
        if sys.version_info.major == 2:
            with open(self.fingerprint_file, "wb") as f:
                json.dump(SSLUtil.fingerprintsLocal, f)
        else:
            with open(self.fingerprint_file, "w", encoding="utf-8") as f:
                json.dump(SSLUtil.fingerprintsLocal, f)


#
# ServiceDiscoveryLogic
#

class ServiceDiscoveryLogic(ScriptedLoadableModuleLogic):
    def run(self, server_url):
        response = requests.get(server_url, timeout=5.0)
        service_list = response.json()

        data = {}

        for service in service_list:
            data[service['modality']] = {}

        for service in service_list:
            data[service['modality']][service['anatomy']] = {}

        for service in service_list:
            data[service['modality']][service['anatomy']][service['task']] = []

        for service in service_list:
            data[service['modality']][service['anatomy']][service['task']].append(service)

        print(data)

        return data


#
# InterfaceDiscoveryLogic
#

class InterfaceDiscoveryLogic(ScriptedLoadableModuleLogic):
    def run(self, server_url):
        response = SSLUtil.get(server_url, timeout=5.0)
        interface = response.json()

        return interface

# base64 utils
def __base64_decode__(data_in):
    if sys.version_info.major == 2:
        return base64.decodestring(data_in)
    else:
        return base64.decodebytes(data_in.encode("ascii"))

def __base64_encode__(data_in):
    if sys.version_info.major == 2:
        return base64.encodestring(data_in)
    else:
        return base64.encodebytes(data_in).decode("ascii")
