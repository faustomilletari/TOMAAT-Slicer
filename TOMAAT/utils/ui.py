import qt, ctk, slicer
import os
import uuid
import tempfile

def decorator(layout):
   pass

def collapsible_button(name):
    coll = ctk.ctkCollapsibleButton()
    coll.text = name
    return coll


def add_image(path):
    logo_label = qt.QLabel()
    logo_label.setAlignment(4)
    print('loading')
    logo_pixmap = \
        qt.QPixmap(path)
    logo_label.setPixmap(logo_pixmap)

    return logo_label, logo_pixmap


def add_textbox(default_text, select_function=None):
    text_box = qt.QLineEdit()
    text_box.text = default_text

    if select_function is not None:
        text_box.connect('textChanged(const QString &)', select_function)

    return text_box


def add_button(text, tooltip_text='', click_function=None, enabled=True):
    button = qt.QPushButton(text)
    button.toolTip = tooltip_text
    button.enabled = enabled
    button.connect('clicked(bool)', click_function)

    return button


def add_label(text):
    label = qt.QLabel()
    label.setText(text)

    return label


class ScalarVolumeWidget(slicer.qMRMLNodeComboBox):
    def __init__(self, destination):
        super(ScalarVolumeWidget, self).__init__()

        self.destination = destination

        self.type = 'ScalarVolumeWidget'

        self.nodeTypes = ['vtkMRMLScalarVolumeNode']
        self.selectNodeUponCreation = True
        self.addEnabled = False
        self.removeEnabled = False
        self.noneEnabled = False
        self.showHidden = False
        self.showChildNodeTypes = False
        self.setMRMLScene(slicer.mrmlScene)
        self.setToolTip('Pick volume')
        self.connect('currentNodeChanged(vtkMRMLNode*)', self.update_viz)

    def update_viz(self):
        for view in ['Red', 'Green', 'Yellow']:
            view_widget = slicer.app.layoutManager().sliceWidget(view)
            view_logic = view_widget.sliceLogic()

            view_logic.GetSliceCompositeNode().SetForegroundVolumeID(self.currentNodeID)
            view_logic.GetSliceCompositeNode().SetBackgroundVolumeID(self.currentNodeID)

            view_logic.GetSliceCompositeNode().SetLabelOpacity(0.5)
            view_logic.FitSliceToAll()

        sliceWidget = slicer.app.layoutManager().sliceWidget('Red')
        sliceLogic = sliceWidget.sliceLogic()
        sliceNode = sliceLogic.GetSliceNode()
        sliceNode.SetSliceVisible(True)

class MarkupsFiducialWidget(slicer.qMRMLNodeComboBox):
    def __init__(self, destination):
        super(MarkupsFiducialWidget, self).__init__()

        self.destination = destination

        self.type = 'MarkupsFiducialWidget'

        self.nodeTypes = ['vtkMRMLMarkupsFiducialNode']
        self.selectNodeUponCreation = True
        self.addEnabled = False
        self.removeEnabled = False
        self.noneEnabled = False
        self.showHidden = False
        self.showChildNodeTypes = False
        self.setMRMLScene(slicer.mrmlScene)
        self.setToolTip('Pick fiducial list')


class SliderWidget(ctk.ctkSliderWidget):
    def __init__(self, minimum, maximum, destination):
        super(SliderWidget, self).__init__()

        self.singleStep = (float(maximum) - float(minimum)) / 200.0

        self.minimum = minimum
        self.maximum = maximum
        self.destination = destination

        self.type = 'SliderWidget'

        self.value = (float(maximum) - float(minimum)) / 2.0

        self.setToolTip('Set value')


class CheckboxWidget(qt.QCheckBox):
    def __init__(self, text, destination):
        super(CheckboxWidget, self).__init__(text)

        self.destination = destination
        self.type = 'CheckboxWidget'

        self.value = False

        self.clicked.connect(self.updateValue)

    def updateValue(self):
        if self.isChecked():
            self.value = True
        else:
            self.value = False


class RadioButtonWidget(qt.QVBoxLayout):
    def __init__(self, options, destination):
        super(RadioButtonWidget, self).__init__()

        for i, option in enumerate(options):
            radio = qt.QRadioButton(option)
            radio.clicked.connect(self.updateValue(radio))

            if i == 0:
                radio.setChecked(True)
                self.value = option

            self.addWidget(radio)

        self.destination = destination
        self.type = 'RadioButtonWidget'

    def updateValue(self, radio):
        def do_update():
            self.value = radio.text
        return do_update








