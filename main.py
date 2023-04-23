import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from ttkthemes import ThemedTk

import sv_ttk
from replit import audio

import os
import json
import copy

from googletrans import Translator
from wrpy import WordReference
from gtts import gTTS

import openai

PROMPTS_PATH = 'prompts.json'
with open(PROMPTS_PATH, 'r') as prompts:
	PROMPTS = json.load(prompts)

openai.api_key = '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'  # os.getenv('open_ai_api_key')

ENGLISH, FRENCH = 'en', 'fr'

BEGINNER_LEVEL = 'Your students are absolute begginers, they know some common words and basic grammar structure but not much else. Please make sure to accomodate the text appropriately.'
INTERMEDIATE_LEVEL = 'Your students are intermediates, they know a decent amount of words and non-complex grammar structures. Please make sure to accomodate the text appropriately.'
ADVANCED_LEVEL = 'Your students are advanced, they know many words and most grammar structures, but they are not quite fluent. Please make sure to accomodate the text appropriately.'


def complete_chat(messages, complete_text=True):
	attempts = 0
	while attempts < 1:
		try:
			results = openai.ChatCompletion.create(
				model="gpt-3.5-turbo",
				messages=messages
			)
			return results['choices'][0]['message']
		except openai.error.RateLimitError:
			attempts += 1
	if not complete_text:
		return None
	return complete_text(messages)


def complete_text(messages):
	prompt = '\n\n'.join(message['content'] for message in messages)
	attempts = 0
	while attempts < 1:
		try:
			results = openai.Completion.create(
			    engine='text-davinci-003',
			    prompt=prompt,
			    temperature=0.7,
			    max_tokens=2048,
			)
			return results['choices'][0]['content']['text']
		except openai.error.RateLimitError:
			attempts += 1
	return None


def display_wr_results(results):
	s = ''
	for translation in results['translations']:
		s += translation['title'] + '\n'
		for i, entry in enumerate(translation['entries'], 1):
			from_word = entry['from_word']
			s += f'    {i}: {from_word["source"]} ({from_word["grammar"]})\n'
			for x in entry['to_word']:
				s += f'          {x["meaning"]}'
				if x['notes']:
					s += f' ({x["notes"]})\n'
				else:
					s += '\n'
			if entry['context']:
				s += f'        Definition: {entry["context"]}\n'
			if entry['from_example'] and entry['to_example']:
				s += f'        Example: {entry["from_example"]}\n'
				s += f'                 {" ".join(entry["to_example"])}\n'
			s += '\n'
		s += '\n\n'
	return s.rstrip()
	

class FrenchHelper:
	def __init__(self, level=BEGINNER_LEVEL):
		self.translator = Translator()
		self.wr_fr_en = WordReference(FRENCH, ENGLISH)
		self.wr_en_fr = WordReference(ENGLISH, FRENCH)
		self.level = level
		self.messages = []
		self.reset_messages()

	def reset_messages(self):
		self.messages = [
			{"role": "system", "content": PROMPTS['context'] + '\n\n' + PROMPTS['general_question']['instructions']}
		]

	def translate_en_to_fr(self, text):
		results = self.translator.translate(text, dest=FRENCH, src=ENGLISH)
		return results.text

	def translate_fr_to_en(self, text):
		results = self.translator.translate(text, dest=ENGLISH, src=FRENCH)
		return results.text

	def word_lookup_fr_to_en(self, word):
		try:
			results = self.wr_fr_en.translate(word)
			return display_wr_results(results)
		except NameError:
			return 'No English to French translation found.'

	def word_lookup_en_to_fr(self, word):
		try:
			results = self.wr_en_fr.translate(word)
			return display_wr_results(results)
		except NameError:
			return 'No English to French translation found.'
	
	def speak_text(self, text, lang=ENGLISH):
		tts = gTTS(text=text, lang=lang)
		path = "temp.mp3"
		tts.save(path)
		source = audio.play_file(path)
		os.remove(path)
		return source

	def gpt_prompt(self, prompt_key, **kwargs):
		prompt = PROMPTS[prompt_key]['instructions'] 
		prompt += '\n\n' + PROMPTS[prompt_key]['substitute_context']
		prompt = prompt.format(**kwargs)
		messages = [
			{"role": "system", "content": PROMPTS['context']},
			{"role": "user", "content": prompt}
		]
		results = complete_chat(messages)
		if isinstance(results, dict):
			results = results['content']
		if results is None:
			return None
		return results.strip()

	def messages_to_text(self, messages):
		text = ''
		for message in messages:
			if message['role'] == 'user':
				text += f'You: {message["content"].strip()}\n\n'
			elif message['role'] == 'assistant':
				text += f'AI: {message["content"].strip()}\n\n'
		return text.strip()

	def general_question(self, question):
		self.messages.append({"role": "user", "content": question})
		results = complete_chat(self.messages, complete_text=False)
		if results is None:
			return None
		self.messages.append(results)
		text = ''
		for message in self.messages:
			if message['role'] == 'user':
				text += f'You: {message["content"].strip()}\n\n'
			elif message['role'] == 'assistant':
				text += f'AI: {message["content"].strip()}\n\n'
		return text.strip()

	def generate_dialog(self):
		return self.gpt_prompt('generate_dialog', level=self.level)

	def generate_article(self):
		return self.gpt_prompt('generate_article', level=self.level)

	def generate_story(self):
		return self.gpt_prompt('generate_story', level=self.level)
	
	def generate_lesson(self):
		return self.gpt_prompt('generate_lesson', level=self.level)


class App(ThemedTk):
	def __init__(self):
		super().__init__(theme='arc')
		self.title("Learn French")

		width, height = 1000, 750
		self.geometry(f'{width}x{height}')

		sv_ttk.set_theme('light')

		self.helper = FrenchHelper()

		self.left = ttk.Frame(self, width=width/2, height=height)
		self.right = ttk.Frame(self, width=width/2, height=height)
		self.left.pack(side=tk.LEFT, fill='both')
		self.right.pack(side=tk.RIGHT, fill='both')
		self.left.grid_propagate(False)
		self.right.grid_propagate(False)

		# Create string vars
		self.level_var = tk.StringVar(self)
		self.level_var.set('Beginner')

		self.trans_var = tk.StringVar(self)
		self.trans_var.set('Text Translation')

		self.lang_var = tk.StringVar(self)
		self.lang_var.set('French to English')

		self.type_var = tk.StringVar(self)
		self.type_var.set('Dialog')

		# Create left widgets
		self.left_widgets = {
			'title': ttk.Label(self.left, text='Welcome to the Learn French app!', font=('Arial', 15)),
			
			'level_label': ttk.Label(self.left, text='Enter your current French level.', font=('Arial', 12)),
			'level_dropdown': ttk.OptionMenu(self.left, self.level_var, 'Beginner', 'Beginner', 'Intermediate', 'Advanced', command=self.set_level),
			
			'chat_label': ttk.Label(self.left, text='French Assistant AI Chat', font=('Arial', 12)),
			'chat_input': ttk.Entry(self.left),
			'chat_function': ttk.Button(self.left, text='Send Chat', command=self.chat),

			'translate_label': ttk.Label(self.left, text='Translation and Dictionary Lookup', font=('Arial', 12)),
			'text_input': ttk.Entry(self.left),
			'translate_or_lookup_dropdown': ttk.OptionMenu(self.left, self.trans_var, 'Text Translation', 'Text Translation', 'Word/Phrase Lookup', command=self.set_trans),
			'fr_or_en_dropdown': ttk.OptionMenu(self.left, self.lang_var, 'French to English', 'French to English', 'English to French'),
			'translate_button': ttk.Button(self.left, text='Translate Text', command=self.translate),

			'generation_label': ttk.Label(self.left, text='Random AI French Text Generation', font=('Arial', 12)),
			'type_dropdown': ttk.OptionMenu(self.left, self.type_var, 'Dialog', 'Dialog', 'Article', 'Story', 'Lesson'),
			'generate_button': ttk.Button(self.left, text='Generate', command=self.generate_text),

			'switch_theme_bottom': ttk.Checkbutton(self.left, text='Dark Theme', style='Switch.TCheckbutton', command=sv_ttk.toggle_theme),
			'speak_output_button_bottom': ttk.Button(self.left, text='Speak Last Output', command=self.speak_last_output)
		}
		for key in self.left_widgets:
			self.left_widgets[key].pack(side=tk.BOTTOM if 'bottom' in key else tk.TOP, padx=10, pady=(30, 10) if 'label' in key else 5)

		self.default_chat_input = 'Enter AI chat/question'
		self.left_widgets['chat_input'].insert(tk.END, self.default_chat_input)
		self.left_widgets['chat_input'].bind('<Button-1>', lambda event: self.clear_text(event, self.default_chat_input))
		self.left_widgets['chat_input'].bind('<FocusOut>', lambda event: self.set_default(event, self.default_chat_input))
		self.left_widgets['chat_input'].bind('<Return>', lambda event: self.chat())

		self.default_text_input = 'Enter text or word/phrase'
		self.left_widgets['text_input'].insert(tk.END, self.default_text_input)
		self.left_widgets['text_input'].bind('<Button-1>', lambda event: self.clear_text(event, self.default_text_input))
		self.left_widgets['text_input'].bind('<FocusOut>', lambda event: self.set_default(event, self.default_text_input))
		self.left_widgets['text_input'].bind('<Return>', lambda event: self.translate())

		# Create right widgets
		self.output = scrolledtext.ScrolledText(self.right, wrap=tk.WORD, width=100, height=100)
		self.output.pack(side=tk.TOP, padx=10, pady=10)
		self.output.config(state=tk.DISABLED)

		self.last = ''
		self.last_language = ENGLISH
		self.source = None

	def run(self):
		self.mainloop()

	def clear_text(self, event, default):
		if event.widget.get() == default:
			event.widget.delete(0, tk.END)
		event.widget.focus()
	
	def set_default(self, event, default):
		if not event.widget.get().strip():
			event.widget.insert(0, default)

	def speak_last_output(self):
		if self.source is not None and not self.source.paused:
			self.source.paused = True
			self.source = None
			self.left_widgets['speak_output_button_bottom'].config(text='Speak Last Output')
		else:
			self.left_widgets['speak_output_button_bottom'].config(text='Preparing Sound...')
			self.update()
			self.source = self.helper.speak_text(self.last, self.last_language)
			self.left_widgets['speak_output_button_bottom'].config(text='Stop Speaking')

	def set_level(self, level):
		if level == 'Beginner':
			self.helper.level = BEGINNER_LEVEL
		elif level == 'Intermediate':
			self.helper.level = INTERMEDIATE_LEVEL
		elif level == 'Advanced':
			self.helper.level = ADVANCED_LEVEL
		else:
			raise ValueError(f'Invalid level value: {level}')

	def set_trans(self, trans):
		if 'Translation' in trans:
			self.left_widgets['translate_button'].config(text='Translate Text')
		elif 'Lookup' in trans:
			self.left_widgets['translate_button'].config(text='Lookup Word/Phrase')
		else:
			raise ValueError(f'Invalid trans value: {trans}')

	def chat(self):
		question = self.left_widgets['chat_input'].get()
		self.left_widgets['chat_input'].delete('0', tk.END)
		
		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		messages = copy.deepcopy(self.helper.messages)
		messages.append({'role': 'user', 'content': question})
		messages.append({'role': 'assistant', 'content': 'Generating text...'})
		self.output.insert('1.0', self.helper.messages_to_text(messages))
		self.output.config(state=tk.DISABLED)
		self.update()
		self.focus()
			
		text = self.helper.general_question(question)
		if text is None:
			text = 'Open AI is currently overloaded with requests. You can retry your request or come back later.'

		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		self.output.insert('1.0', text)
		self.output.config(state=tk.DISABLED)

		self.left_widgets['chat_input'].insert(tk.END, 'Enter AI chat/question')

		self.last = self.helper.messages[-1]['content']
		self.last_language = ENGLISH

	def translate(self):
		text_input = self.left_widgets['text_input'].get()
		translate = 'Translation' in self.trans_var.get()
		en_to_fr = 'to French' in self.lang_var.get()
		
		self.left_widgets['text_input'].delete('0', tk.END)
		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		if translate:
			self.output.insert('1.0', 'Requesting text translation, please wait...')
		else:
			self.output.insert('1.0', 'Requesting word/phrase information, please wait...')
		self.output.config(state=tk.DISABLED)
		self.update()
		self.focus()
		
		if translate and en_to_fr:
			text = self.helper.translate_en_to_fr(text_input)
		elif translate and not en_to_fr:
			text = self.helper.translate_fr_to_en(text_input)
		elif en_to_fr:
			text = self.helper.word_lookup_en_to_fr(text_input)
		else:
			text = self.helper.word_lookup_fr_to_en(text_input)

		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		self.output.insert('1.0', text)
		self.output.config(state=tk.DISABLED)

		self.left_widgets['text_input'].insert(tk.END, 'Enter text or word/phrase')

		self.last = text
		self.last_language = FRENCH if en_to_fr else ENGLISH

	def generate_text(self):
		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		self.output.insert('1.0', 'Requesting AI text generation, please wait...')
		self.output.config(state=tk.DISABLED)
		self.update()

		type_ = self.type_var.get()
		if type_ == 'Dialog':
			text = self.helper.generate_dialog()
		elif type_ == 'Article':
			text = self.helper.generate_article()
		elif type_ == 'Story':
			text = self.helper.generate_story()
		elif type_ == 'Lesson':
			text = self.helper.generate_lesson()
		else:
			raise ValueError(f'Invalid type value: {type_}')
		if text is None:
			text = 'Open AI is currently overloaded with requests. You can retry your request or come back later.'

		self.output.config(state=tk.NORMAL)
		self.output.delete('1.0', tk.END)
		self.output.insert('1.0', text)
		self.output.config(state=tk.DISABLED)

		self.last = text
		self.last_language = FRENCH


def main():
	app = App()
	app.run()


if __name__ == '__main__':
	main()
	