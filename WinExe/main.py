from kivy.app import App

from kivy.properties import ObjectProperty,ListProperty,StringProperty
from kivy.core.window import Window

from kivy.uix.tabbedpanel import TabbedPanel,TabbedPanelHeader
from kivy.uix.stacklayout import StackLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.lang import Builder

from threading import Thread
from pydub import AudioSegment
import os

STATE_COLORS = {
	"pending":(0.1,.1,1,1),
	"done":(0.1,1,0.1,1),
	"error":(1,0.1,0.1,1),
	"ignored":(1,0.1,0.1,1),
	"unknown":(0.3,0.3,0.3,1),
}

Builder.load_string('''
<LoadDialogMul>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        FileChooserIconView:
            id: filechooser
            multiselect: True

        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Cancel"
                on_release: root.cancel()

            Button:
                text: "Load"
                on_release: root.load(filechooser.path, filechooser.selection)
<LoadDialogDir>:
    BoxLayout:
        size: root.size
        pos: root.pos
        orientation: "vertical"
        FileChooserIconView:
            id: filechooser
            dirselect: True
            filter_dir: False
            filters: [root.NoFile]
        BoxLayout:
            size_hint_y: None
            height: 30
            Button:
                text: "Cancel"
                on_release: root.cancel()

            Button:
                text: "Load"
                on_release: root.load(filechooser.path, filechooser.selection)
<CustomGridLayout>:
	canvas.before:
		Color:
			rgba: 1, 1, 1, 1
		Rectangle:
			pos: 0,0
			size: self.width, self.height
		Color:
			rgba: .5, .5, .5, 1
		Line:
		    width: 2
		    rectangle: 0,0, self.width, self.height
''')



AUDIO_FORMATS = [
	"MP3", "wma","flv"
]

DESTINATION_FOLDER = '.'

class Converter(Thread):
	"""docstring for Converter"""
	def __init__(self,lst,from_,to_,statecallback,*args,**kwargs):
		super(Converter, self).__init__(*args,**kwargs)
		self.list = lst
		self.from_ = from_
		self.to_ = to_
		self.statecallback = statecallback

		self.enabled = False

	def convert_file(self,src,dst,from_,to_):
		print('converting {} to destination {} from format {} to format {}'.format(
			src,dst,from_,to_
		))
		song = AudioSegment.from_file(src,from_)
		song.export(os.path.join(DESTINATION_FOLDER,dst), format=to_)

	def run(self):
		to_conv = [l for l in self.list if l['state'] == "pending"]
		while len(to_conv):
			if not self.enabled:
				break
			next_ = to_conv.pop(0)
			self.statecallback(next_['file'],'converting')
			dst = os.path.split(next_['file'])[1]
			dst = dst[:-1*len(self.from_)]+self.to_
			try:
				self.convert_file(next_['file'],dst,self.from_,self.to_)
			except:
				self.statecallback(next_['file'],'error')
			else:	
				self.statecallback(next_['file'],'done')
			to_conv = [l for l in self.list if l['state'] == "pending"]

		

class FilesHolder(object):

	"""docstring for FilesHolder"""
	def __init__(self, GrList):
		super(FilesHolder, self).__init__()
		self.trg_format = None
		self.GrList = GrList

	def set_format(self,format_):
		self.trg_format = format_
		for file in self.GrList.FlList:
			if self.trg_format is None:
				self.change_state(file['file'],"unknown")
			else:
				if file['format'].lower() != self.trg_format.lower():
					self.change_state(file['file'],"ignored")
				else:
					self.change_state(file['file'],"pending")

	def append(self,file):
		state = "pending"
		format_ = file.split('.')[-1]
		if self.trg_format is None:
			state = "unknown"
		elif format_.lower() != self.trg_format.lower():
			state = 'ignored'

		new_file = {
			"file":file,
			"format":format_,
			"state":state,
			"lab":Label(text=state,size_hint=(1,None),height=20,color=STATE_COLORS[state])
		}
		self.GrList.FlList.append(new_file)
		text = new_file['file'] if len(new_file['file']) < 55 else '...'+new_file['file'][-55:]
		textformat = new_file['format'] if len(new_file['format']) < 7 else '?'
		self.GrList.add_widget(Label(text=text,size_hint=(1,None),height=20,color=(0,0,0,1)))
		self.GrList.add_widget(Label(text=new_file['format'],size_hint=(1,None),height=20,color=(0,0,0,1)))
		self.GrList.add_widget(new_file['lab'])

	def change_state(self,file,new_state):
		try:
			idx = [f['file'] for f in self.GrList.FlList].index(file)
		except:
			return None
		self.GrList.FlList[idx]['state'] = new_state
		self.GrList.FlList[idx]['lab'].text = new_state
		try:
			self.GrList.FlList[idx]['lab'].color = STATE_COLORS[new_state]
		except:
			self.GrList.FlList[idx]['lab'].color = (0,0,0,1)

class TargetDirectoryHolder(object):
	"""docstring for TargetDirectoryHolder"""
	def __init__(self, TItarget):
		super(TargetDirectoryHolder, self).__init__()
		self.TITarget = TItarget
		self.target = ''

	def append(self,path):
		self.target = path
		self.TItarget.text = self.target
		DESTINATION_FOLDER = self.target
		

class LoadDialogDir(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)

    def NoFile(self,dir,file):
    	return False

class LoadDialogMul(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class CustomGridLayout(GridLayout):
	"""docstring for CustomGridLayout"""
	FlList = ListProperty(None)	
		


class ConverterApp(App):
	converter = None
	started = False

	"""docstring for ConverterApp"""
	def dismiss_popup(self):
		self._popup.dismiss()

	def show_errors(self,errors):
		content = GridLayout();content.cols=1
		for error in errors:
			content.add_widget(Label(text=error))
		self._popup = Popup(
			title="Error", content=content,
			size_hint=(0.5, None)
		)
		self._popup.open()

	def Start_Converting(self,e):
		errors = []
		if not hasattr(self,"input_format"):
			errors.append('Specify the input format')
		if not hasattr(self,"output_format"):
			errors.append('Specify the output format')

		if len(errors):
			self.show_errors(errors)
			return None

		if self.converter is None:
			self.converter = Converter(
				self.AudioFls_toconvert.GrList.FlList,
				self.input_format,self.output_format,
				self.AudioFls_toconvert.change_state
			)
		if self.converter.enabled == False:
			if self.started == True:
				self.converter = Converter(
					self.AudioFls_toconvert.GrList.FlList,
					self.input_format,self.output_format,
					self.AudioFls_toconvert.change_state
				)
				self.started = True
			self.converter.enabled = True
			self.converter.start()

	def Stop_Converting(self,e):
		if not self.converter is None:
			self.converter.enabled = False

	def to_path_wrapper(self,obj):
		def to_path(pth,filename):
			for file in filename:
				obj.append(file)
			self.dismiss_popup()
		return to_path

	def GetAudioConversionUI(self):
		self.AudioFls_toconvert = FilesHolder(None)
		self.AudioTarget_Dir = TargetDirectoryHolder(None)

		gl = StackLayout(spacing=(0,5))

		lab_title = Label(text='Audio Format Converter',size_hint=(1,0.1))
		lab_title.outline_color = (1,1,1,1)
		lab_title.color=(0,0,0,1)
		lab_title.outline_width = 2

		sub_gl = GridLayout(cols_minimum={0:20,5:80},size_hint=(1,0.1));sub_gl.cols=6
		sub_gl.add_widget(Label(size_hint=(1,0.8)));
		sub_gl.add_widget(Label(text='From',size_hint=(1,0.8)))
		
		self.input_ext_dd = DropDown()
		for out in AUDIO_FORMATS:
			btn  = Button(text=out,size_hint_y=None, height=44)
			def fnc(e):
				self.input_ext_dd.select(e.text)
				self.input_format = e.text
				self.AudioFls_toconvert.set_format(e.text)
			btn.bind(on_press=fnc)
			self.input_ext_dd.add_widget(btn)
		mainbutton_in = Button(text='Input file format', size_hint=(1,0.8))
		mainbutton_in.bind(on_release=self.input_ext_dd.open)
		self.input_ext_dd.bind(on_select=lambda instance, x: setattr(mainbutton_in, 'text', x))

		sub_gl.add_widget(mainbutton_in)
		sub_gl.add_widget(Label(text='To',size_hint=(1,0.8)))
		self.output_ext_dd = DropDown()
		for out in AUDIO_FORMATS:
			btn  = Button(text=out,size_hint_y=None, height=44)
			def fnc(e):
				self.output_ext_dd.select(e.text)
				self.output_format = e.text
			btn.bind(on_press=fnc)
			self.output_ext_dd.add_widget(btn)
		mainbutton_out = Button(text='Output file format', size_hint=(1,0.8))
		mainbutton_out.bind(on_release=self.output_ext_dd.open)
		self.output_ext_dd.bind(on_select=lambda instance, x: setattr(mainbutton_out, 'text', x))

		sub_gl.add_widget(mainbutton_out)
		sub_gl.add_widget(Label(size_hint=(1,0.8)))
		sub_gl.add_widget(Label());sub_gl.add_widget(Label());sub_gl.add_widget(Label());sub_gl.add_widget(Label());sub_gl.add_widget(Label());sub_gl.add_widget(Label());

		sub_gl_1 = GridLayout(cols_minimum={0:350,1:50,2:50},size_hint=(1,0.1));sub_gl_1.cols=3

		sub_gl_1.add_widget(Label(text='Filename'))
		sub_gl_1.add_widget(Label(text='format'))
		sub_gl_1.add_widget(Label(text='state'))

		scroll = ScrollView(do_scroll_y=True,size_hint=(1, None), size=(Window.width, 200))
		sub_gl_1_1 = CustomGridLayout(cols_minimum={0:350,1:50,2:50},size_hint=(1,None),height=200);sub_gl_1_1.cols=3
		sub_gl_1_1.bind(minimum_height=sub_gl_1_1.setter('height'))
		self.AudioFls_toconvert.GrList = sub_gl_1_1
		scroll.add_widget(sub_gl_1_1)

		sub_gl_2 = StackLayout(orientation='rl-tb',size_hint=(1,0.02))
		sub_gl_2.add_widget(Label(text='',width=50,height=30,size_hint=(None, None)))
		sub_gl_2.add_widget(Button(text='Remove File',width=100,height=30,size_hint=(None, None)))
		def show_load(e):
			content = LoadDialogMul(
				load=self.to_path_wrapper(self.AudioFls_toconvert), cancel=self.dismiss_popup,
			)
			self._popup = Popup(
				title="Load file(s)", content=content,
				size_hint=(0.9, 0.9)
			)
			self._popup.open()
		btn  = Button(text='Add File(s)',width=100,height=30,size_hint=(None, None))
		btn.bind(on_release=show_load)
		sub_gl_2.add_widget(btn)

		sub_gl_3 = GridLayout(cols_minimum={1:120,2:500,3:50},size_hint=(1,0.05));sub_gl_3.cols=4
		sub_gl_3.add_widget(Label(text='',width=50,height=30,size_hint=(None, None)))
		sub_gl_3.add_widget(Label(text='Dest. Directory: ',width=120,height=30,size_hint=(None, None)))
		self.AudioTarget_Dir.TItarget = TextInput(multiline=False,width=500,height=30,size_hint=(None, None))
		sub_gl_3.add_widget(self.AudioTarget_Dir.TItarget)
		def show_load2(e):
			content = LoadDialogDir(
				load=self.to_path_wrapper(self.AudioTarget_Dir), cancel=self.dismiss_popup,
			)
			self._popup = Popup(
				title="Choose Directory", content=content,
				size_hint=(0.9, 0.9)
			)
			self._popup.open()
		btn2 = Button(text='parcourir',width=100,height=30,size_hint=(None, None))
		btn2.bind(on_release=show_load2)
		sub_gl_3.add_widget(btn2)

		sub_gl_4 = StackLayout(orientation='rl-tb',size_hint=(1,0.04),spacing=(0,10))
		sub_gl_4.add_widget(Label(text='',width=50,height=30,size_hint=(None, None)))

		btn4 = Button(text='Stop',width=100,height=30,size_hint=(None, None))
		btn4.bind(on_release=self.Stop_Converting)
		sub_gl_4.add_widget(btn4)

		btn3 = Button(text='Start',width=100,height=30,size_hint=(None, None))
		btn3.bind(on_release=self.Start_Converting)
		sub_gl_4.add_widget(btn3)

		gl.add_widget(lab_title)
		gl.add_widget(sub_gl)
		header = Label(text='Files to convert:(0 pending, 0 done)',size_hint=(1,0.05))
		def changeHeader(e,filelist):
			header.text = 'Files to convert:({} pending, {} done)'.format(
				len([f for f in filelist if f['state'] == 'pending']),
				len([f for f in filelist if f['state'] == 'done']),
			)
		sub_gl_1_1.bind(FlList=changeHeader)
		gl.add_widget(header)
		gl.add_widget(sub_gl_1)
		gl.add_widget(scroll)
		gl.add_widget(sub_gl_2)
		gl.add_widget(Label(text='',height=40,size_hint=(None,0.04)))
		gl.add_widget(sub_gl_3)
		gl.add_widget(Label(text='',height=40,size_hint=(None,0.03)))
		gl.add_widget(sub_gl_4)

		return gl

	def GetVideoConversionUI(self):
		gl = GridLayout();gl.cols=1
		lab_title = Label(text='Video Format Converter')
		lab_title.outline_color = (1,1,1,1)
		lab_title.color=(0,0,0,1)
		lab_title.outline_width = 2
		gl.add_widget(lab_title)
		return gl

	def build(self):
		self.title = 'Converter'
		tabs= TabbedPanel(do_default_tab=False)
		th = TabbedPanelHeader(text='Audio')
		th.content = self.GetAudioConversionUI()
		th1 = TabbedPanelHeader(text='Video')
		th1.content = self.GetVideoConversionUI()

		tabs.add_widget(th)
		tabs.add_widget(th1)

		return tabs

if __name__ == '__main__':
	app = ConverterApp()
	app.run()
