import utils.dependencies

import base64
import logging
import os
import tempfile
import uuid

import ctk
import qt
import requests
import slicer

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from slicer.ScriptedLoadableModule import *

from utils.ui import ScalarVolumeWidget, SliderWidget, CheckboxWidget, RadioButtonWidget
from utils.ui import collapsible_button, add_image, add_textbox, add_button, add_label


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

    self.urlBoxDirectConnection = add_textbox("http://localhost:9000", self.select_from_textbox)

    self.directConnectionLayout.addRow("Server URL: ", self.urlBoxDirectConnection)

    directConnectionCollapsibleButton.collapsed = True

    #
    # Managed Connection area
    #
    managedConenctionCollapsibleButton = collapsible_button('Public Server List')
    self.layout.addWidget(managedConenctionCollapsibleButton)

    self.managedConnectionLayout = qt.QFormLayout(managedConenctionCollapsibleButton)

    self.urlBoxManagedConnection = add_textbox("http://tomaat.cloud:8000/discover")

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
    print 'USING HOST IN DIRECT CONNECTION PANE'
    self.predictionUrl = self.urlBoxDirectConnection.text + '/predict'
    self.interfaceUrl = self.urlBoxDirectConnection.text + '/interface'
    self.serviceDescription.setText('')

    logic = InterfaceDiscoveryLogic()

    interface_specification = logic.run(self.interfaceUrl)

    self.add_widgets(interface_specification)

  def select_from_tree(self):
    item = self.serviceTree.selectedItems()
    item = item[0]

    if isinstance(item, ServiceEntry):
      self.predictionUrl = item.endpoint_data['prediction_url']
      self.interfaceUrl = item.endpoint_data['interface_url']
      self.serviceDescription.setText(item.endpoint_data['description'])

    logic = InterfaceDiscoveryLogic()

    interface_specification = logic.run(self.interfaceUrl)

    self.add_widgets(interface_specification)

  def onDiscoverButton(self):
    logic = ServiceDiscoveryLogic()

    self.serviceTree.clear()

    data = logic.run(self.urlBoxManagedConnection.text)

    for modality in data.keys():
      mod_item = qt.QTreeWidgetItem()
      mod_item.setText(0, 'Modality: ' + str(modality))

      self.serviceTree.addTopLevelItem(mod_item)

      for anatomy in data[modality].keys():
        anatom_item = qt.QTreeWidgetItem()
        anatom_item.setText(0, 'Anatomy: ' + str(anatomy))

        mod_item.addChild(anatom_item)

        for task in data[modality][anatomy].keys():
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
    self.urlBoxDirectConnection.text = "http://localhost:9000"
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

    self.clearToSendMsg=False

    print 'CONNECTING TO SERVER {}'.format(self.predictionUrl)

    progress_bar = slicer.util.createProgressDialog(labelText="Uploading to remote server", windowTitle="Uploading...")
    progress_bar.setCancelButton(0)

    logic.run(
      self.widgets, self.predictionUrl, progress_bar
    )


def create_callback(encoder, progress_bar):
  encoder_len = encoder.len

  def callback(monitor):
    progress_bar.value = float(monitor.bytes_read)/float(encoder_len) * 100

  return callback


#
# TOMAATLogic
#

class TOMAATLogic(ScriptedLoadableModuleLogic):
  message = {}
  savepath = tempfile.gettempdir()
  node_name = None

  list_files_cleanup = []

  def add_scalar_volume_to_message(self, widget):
    id = uuid.uuid4()
    tmp_filename_mha = os.path.join(self.savepath, str(id) + '.mha')
    slicer.util.saveNode(widget.currentNode(), tmp_filename_mha)

    self.node_name = widget.currentNode().GetName()

    self.message[widget.destination] = ('filename', open(tmp_filename_mha, 'rb'), 'text/plain')

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

  def add_slider_value_to_message(self, widget):
    self.message[widget.destination] = str(widget.value)

  def add_checkbox_value_to_message(self, widget):
    self.message[widget.destination] = str(widget.value)

  def add_radiobutton_value_to_message(self, widget):
    self.message[widget.destination] = str(widget.value)

  def receive_label_volume(self, data):
    tmp_segmentation_mha = os.path.join(self.savepath,  self.node_name + '_result'+ '.mha')
    with open(tmp_segmentation_mha, 'wb') as f:
      f.write(base64.decodestring(data['content']))

    success, node = slicer.util.loadLabelVolume(tmp_segmentation_mha, returnNode=True)

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

  def receive_vtk_mesh(self, data):
    tmp_mesh_vtk = os.path.join(self.savepath, self.node_name + data['label'] + '_mesh' + '.vtk')
    with open(tmp_mesh_vtk, 'wb') as f:
      f.write(base64.decodestring(data['content']))
    slicer.util.loadModel(tmp_mesh_vtk)

    os.remove(tmp_mesh_vtk)

  def receive_fiducials(self, data):
    tmp_fiducials_fcsv = os.path.join(self.savepath, self.node_name + data['label'] + '_fiducials' + '.fcsv')
    with open(tmp_fiducials_fcsv, 'wb') as f:
      f.write(base64.decodestring(data['content']))
    slicer.util.loadFiducialList(tmp_fiducials_fcsv)

  def receive_plain_text(self, data):
    slicer.util.messageBox(data['content'], windowTitle=data['label'])

  def run(self, widgets, server_url, progress_bar):
    logging.info('Processing started')

    for widget in widgets:
      if widget.type == 'ScalarVolumeWidget':
        self.add_scalar_volume_to_message(widget)

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

    reply = requests.post(server_url, data=monitor, headers={'Content-Type': monitor.content_type})

    print 'MESSAGE SENT'

    responses_json = reply.json()

    print 'RESPONSE RECEIVED'

    for response in responses_json:
      if response['type'] == 'LabelVolume':
        self.receive_label_volume(response)

      if response['type'] == 'VTKMesh':
        self.receive_vtk_mesh(response)

      if response['type'] == 'Fiducials':
        self.receive_fiducials(response)

      if response['type'] == 'PlainText':
        self.receive_plain_text(response)

    self.cleanup()

    print 'DONE'
    
    return

  def cleanup(self):
    for file in self.list_files_cleanup:
      os.remove(file)

#
# ServiceDiscoveryLogic
#

class ServiceDiscoveryLogic(ScriptedLoadableModuleLogic):
  def run(self, server_url):
    response = requests.get(server_url)
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

    print data

    return data


#
# InterfaceDiscoveryLogic
#

class InterfaceDiscoveryLogic(ScriptedLoadableModuleLogic):
  def run(self, server_url):
    response = requests.get(server_url)
    interface = response.json()

    return interface


