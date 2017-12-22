import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import os
import numpy as np

try:
  import requests
except:
  import pip
  pip.main(['install','requests'])
  import requests
  pass

import json
import uuid
import base64
import sys
import tempfile
#
# TOMAAT
#


module_version = 0.01


class TOMAAT(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "TOMAAT" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Fausto Milletari"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
      This module performs segmentation of anatomical structures in volumetric medical data using 3D convolutional neural 
      networks in (Mainly V-Net - Milletari et al, 2016). It is intended as a proof of concept and a research module only.
      The computation of the results is offloaded to remote host. You need a fast connection to obtain satisfactory results. 
      In no way the results provided by this model should be trusted to make any clinical judgement. 
      This module is provided without any guarantee about its functionality, precision and correctness of the results.
      This module works by exchanging data (medical images) over the network. There is no guarantee about the destiny of data
      sent through this model to any remote host. Normally data gets processed and then deleted but this cannot be 
      formally guaranteed. Also, no guarantees about privacy can be made. You are responsible for the anonimization of the data 
      you use to run inference. 
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
      ToDo.
""" # replace with organization, grant and thanks.


#
# TOMAATWidget
#

class TOMAATWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.serverUrl = ''

    # Instantiate and connect widgets ...

    #
    # LOGO area
    #
    logoCollapsibleButton = ctk.ctkCollapsibleButton()
    logoCollapsibleButton.text = "Info"
    self.layout.addWidget(logoCollapsibleButton)

    self.logolayout = qt.QFormLayout(logoCollapsibleButton)

    self.logolabel = qt.QLabel()
    self.logolabel.setAlignment(4)
    self.logopixmap = qt.QPixmap(os.path.join(os.path.split(os.path.realpath(__file__))[0], "Resources/Icons/TOMAAT.png"))
    self.logolabel.setPixmap(self.logopixmap)

    self.logolayout.addRow(self.logolabel)

    #
    # Direct Connection area
    #
    directConnectionCollapsibleButton = ctk.ctkCollapsibleButton()
    directConnectionCollapsibleButton.text = "Direct Connection"
    self.layout.addWidget(directConnectionCollapsibleButton)
    self.directConnectionLayout = qt.QFormLayout(directConnectionCollapsibleButton)

    self.urlBoxDirectConnection = qt.QLineEdit()
    self.urlBoxDirectConnection.text = "http://localhost:9000"
    self.urlBoxDirectConnection.connect('textChanged(const QString &)', self.select_from_textbox)

    self.directConnectionLayout.addRow("Server URL: ", self.urlBoxDirectConnection)

    #
    # Managed Connection area
    #
    managedConenctionCollapsibleButton = ctk.ctkCollapsibleButton()
    managedConenctionCollapsibleButton.text = "Public Server List"
    self.layout.addWidget(managedConenctionCollapsibleButton)
    self.managedConnectionLayout = qt.QFormLayout(managedConenctionCollapsibleButton)

    self.urlBoxManagedConnection = qt.QLineEdit()
    self.urlBoxManagedConnection.text = "http://tomaat.cloud:8000/discover"
    self.managedConnectionLayout.addRow("Discovery Server URL: ", self.urlBoxManagedConnection)

    self.serviceCombo = qt.QComboBox()
    self.serviceCombo.currentIndexChanged.connect(self.select_from_combobox)

    self.managedConnectionLayout.addRow(self.serviceCombo)

    self.discoverServicesButton = qt.QPushButton("Discover Services")
    self.discoverServicesButton.toolTip = "Discover available segmentation services on the net."
    self.discoverServicesButton.enabled = True
    self.discoverServicesButton.connect('clicked(bool)', self.onDiscoverButton)

    self.serviceDescription = qt.QLabel()
    self.serviceDescription.setText('')

    self.managedConnectionLayout.addRow(self.discoverServicesButton)

    self.managedConnectionLayout.addRow(self.serviceDescription)

    # layout


    #self.urlBox = qt.QLineEdit()
    #self.urlBox.text = "http://localhost:9000"
    #connectionFormLayout.addRow("Server URL: ", self.urlBox)

    #
    # Segmentation Area
    #
    segmentationCollapsibleButton = ctk.ctkCollapsibleButton()
    segmentationCollapsibleButton.text = "Segmentation"
    self.layout.addWidget(segmentationCollapsibleButton)

    # Layout within the dummy collapsible button
    segmentationFormLayout = qt.QFormLayout(segmentationCollapsibleButton)

    #
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene(slicer.mrmlScene)
    self.inputSelector.setToolTip("Pick the input to the algorithm.")
    segmentationFormLayout.addRow("Input Volume: ", self.inputSelector)

    #
    # threshold value
    #
    self.imageThresholdSliderWidget = ctk.ctkSliderWidget()
    self.imageThresholdSliderWidget.singleStep = 0.01
    self.imageThresholdSliderWidget.minimum = 0
    self.imageThresholdSliderWidget.maximum = 1
    self.imageThresholdSliderWidget.value = 0.5
    self.imageThresholdSliderWidget.setToolTip(
      "Set threshold value for computing the output image. Voxels that lower than this value will set to zero.")
    segmentationFormLayout.addRow("Segmentation threshold", self.imageThresholdSliderWidget)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Segment")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    segmentationFormLayout.addRow(self.applyButton)

    self.time = qt.QLabel()
    self.time.setText('Inference time: ---')
    segmentationFormLayout.addRow(self.time)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputSelector.currentNode()

  def select_from_textbox(self):
    print 'USING HOST IN DIRECT CONNECTION PANE'
    self.serverUrl = self.urlBoxDirectConnection.text
    self.serviceDescription.setText('')

  def select_from_combobox(self):
    print 'USING HOST SELECTED FROM SERVICE LIST'
    index = self.serviceCombo.currentIndex
    self.serverUrl = self.hosts_list[index]
    self.serviceDescription.setText(self.descriptions_list[index])

  def onDiscoverButton(self):
    logic = ServiceDiscoveryLogic()
    texts, self.hosts_list, self.descriptions_list = logic.run(self.urlBoxManagedConnection.text)

    self.serviceDescription.setText('')
    self.serviceCombo.clear()

    for text in texts:
      self.serviceCombo.addItem(text)

  def onConnectDirectlyButton(self):
    for elem in self.removeListGuiReset:
      self.delete_element(elem)
    self.removeListGuiReset = []

    self.urlBoxDirectConnection = qt.QLineEdit()
    self.urlBoxDirectConnection.text = "http://localhost:9000"
    self.connectionFormLayout.addRow("Server URL: ", self.urlBoxDirectConnection)

    self.removeListGuiReset += [self.urlBoxDirectConnection]

  def onApplyButton(self):
    logic = TOMAATLogic()

    if self.serverUrl == '':
      print 'NO SERVER HAS BEEN SPECIFIED'
      return

    print 'CONNECTING TO SERVER {}'.format(self.serverUrl)

    elap_time, volumeNode = logic.run(self.inputSelector.currentNode(), self.imageThresholdSliderWidget.value, self.serverUrl)

    self.time.setText('Inference time: {} ms'.format(np.round(elap_time)))

    logic = slicer.modules.volumerendering.logic()
    volumeNode = slicer.util.getNode(volumeNode.GetName())
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

      view_logic.GetSliceCompositeNode().SetForegroundVolumeID(self.inputSelector.currentNode().GetID())
      view_logic.GetSliceCompositeNode().SetBackgroundVolumeID(self.inputSelector.currentNode().GetID())

      view_logic.GetSliceCompositeNode().SetLabelOpacity(0.5)
      view_logic.FitSliceToAll()

    sliceWidget = slicer.app.layoutManager().sliceWidget('Red')
    sliceLogic = sliceWidget.sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()
    sliceNode.SetSliceVisible(True)


#
# TOMAATLogic
#

class TOMAATLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def hasImageData(self, volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False

    return True

  def run(self, inputVolume, imageThreshold, server_url):
    """
    Run the actual algorithm
    """
    savepath = tempfile.gettempdir()

    if not self.isValidInputOutputData(inputVolume):
      slicer.util.errorDisplay('Input volume is invalid')
      return False

    if not self.hasImageData(inputVolume):
      slicer.util.errorDisplay('Input volume has no image data')
      return False
    try:
      node = slicer.util.getNode('result*')
      slicer.mrmlScene.RemoveNode(node)
    except:
      pass

    logging.info('Processing started')

    id = uuid.uuid4()
    tmp_filename_mha = os.path.join(savepath, str(id) + '.mha')
    tmp_segmentation_mha = os.path.join(savepath, inputVolume.GetName() + '_segmentation' + '.mha')

    # prepare data for processing
    slicer.util.saveNode(inputVolume, tmp_filename_mha)

    with open(tmp_filename_mha, 'rb') as f:
      message = {
        'content_mha': base64.encodestring(f.read()),
        'threshold': imageThreshold,
        'module_version': module_version,
        'modality': 'MRI',
        'anatomy': 'Prostate',
      }

      print 'MESSAGE Prepared, size {}'.format(sys.getsizeof(message))

      response = requests.post(server_url, data=json.dumps(message))

      print 'MESSAGE SENT'

    response_json = response.json()

    print 'RESPONSE RECEIVED'

    if response_json['status'] != 0:
      print response_json['error']
      raise ValueError

    with open(tmp_segmentation_mha, 'wb') as f:
      f.write(base64.decodestring(response_json['content_mha']))

    success, node = slicer.util.loadLabelVolume(tmp_segmentation_mha, returnNode=True)

    os.remove(tmp_filename_mha)
    os.remove(tmp_segmentation_mha)

    return response_json['time'], node


#
# ServiceDiscoveryLogic
#

class ServiceDiscoveryLogic(ScriptedLoadableModuleLogic):
  def run(self, server_url):
    response = requests.get(server_url)
    json = response.json()

    modalities = json['modalities']
    anatomies = json['anatomies']
    hosts = json['hosts']
    descriptions = json['descriptions']

    text, url, descr = [], [], []
    for m, a, h, d in zip(modalities, anatomies, hosts, descriptions):
      text.append(m + ':' + a)
      url.append(h)
      descr.append(d)

    return text, url, descr


