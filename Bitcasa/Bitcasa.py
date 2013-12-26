# Bitcasa Python Class v2 (Still Unofficial) #
# 2013 Michael Thomas (Biscuit Labs) #

# System Imports
import os, sys, json, time
# Requests Imports
import requests
# Multipart Form Encoding
import codecs, mimetypes, sys, uuid
# Multithreading (planned for Uploads, then slowly roll out to other ops - need to discuss)
# http://code.google.com/p/pyloadtools/wiki/CodeTutorialMultiThreading
# from threading import Thread
# Watchdog (for monitoring mirrored folders)
# from watchdog.observers import Observer
# from watchdog.events import LoggingEventHandler

# Bitcasa Uploader Class
class BitcasaUploader(object):
	def __init__(self, filename, chunksize=1 << 13):
		self.filename = filename
		self.chunksize = chunksize
		self.totalsize = os.path.getsize(filename)
		self.readsofar = 0
		# Form Multipart
		self.encoder = codecs.getencoder('utf-8')
		self.boundary = uuid.uuid4().hex
		self.content_type = 'multipart/form-data; boundary={}'.format(self.boundary)

	def __iter__(self):
		with open(self.filename, 'rb') as file:
			# Start Multipart
			form_header = str('--'+self.boundary+'\r\nContent-Disposition: form-data; name="file"; filename="'+self.filename+'"\r\nContent-Type: '+'application/octet-stream'+'\r\n\r\n').encode('utf-8')
			yield form_header
			self.time = time.time()
			while True:
				data = file.read(self.chunksize)
				if not data:
					total_time = time.time() - self.time
					sys.stderr.write("\rFinished uploading file: " + self.filename + " (took "+ str(round(total_time,2)) +" seconds)\n")
					# Finish Multipart
					form_footer = str('\r\n--'+self.boundary+'--\r\n').encode('utf-8')
					yield form_footer
					break
				self.readsofar += len(data)
				percent = self.readsofar * 1e2 / self.totalsize
				sys.stderr.write("\rUploading file: " + self.filename + " {percent:3.0f}%".format(percent=percent))
				yield data
	
	def __len__(self):
		return self.totalsize

class BitcasaUploaderFileAdapter(object):
	def __init__(self, iterable):
		self.iterator = iter(iterable)
		self.length = len(iterable)

	def read(self, size=-1): # TBD: add buffer for `len(data) > size` case
		return next(self.iterator, b'')

	def __len__(self):
		return self.length
		
# Bitcasa Client
class Client:
	# Start Client & Load Config
	def __init__ (self, config_path, verbose=False):
		self.config_path = config_path
		if(self.config_path != None):
			# See if config.json is around.
			# @todo - Defaults if the file isn't found
			try:
				with open(self.config_path, 'r') as config_file:
					self.config = json.load(config_file)
			except Exception as exc:
				raise Exception("Could not find configuration file.")
		else:
			raise Exception("You must specify a config.json path.")

		# Set Class Variables
		# Bitcasa API URL
		self.api_url = self.config['api_url']
		# Bitcasa File API URL (this may replace the above)
		self.file_api_url = self.config['file_api_url']
		# Application Client ID (Create in Bitcasa App Console)
		self.client_id = self.config['client_id']
		# Application Secret (Create in Bitcasa App Console)
		self.secret = self.config['secret']
		# Redirect URL - You can set to whatever, we just need the auth_token
		self.redirect_url = self.config['redirect_url']
		# Auth Token - Auth Token to get API Access Token
		self.auth_token = self.config['auth_token']
		# API Access Token
		self.access_token = self.config['access_token']
		# File Cache Support (if caching is enabled)
		self.cache_dir = self.config['cache_dir']
		# Verbosity
		self.verbose = verbose

		# Check to see if we need to create a cache
		if(self.cache_dir == None):
			self.cache_dir = os.path.dirname(os.path.realpath(__file__)) + ".cache"
			self.save_config()
		# Make sure cache exists & create one if it doesn't
		if not os.path.exists(self.cache_dir):
			os.makedirs(self.cache_dir)
		
		# See if we need auth_token & access token.
		if(self.auth_token == "") or (self.access_token == ""):
			self.authenticate()

	# Write to configuration file
	def save_config (self):
		with open(self.config_path, 'w') as outfile:
			json.dump(self.config, outfile, indent=4)

	# Authenticate application & get tokens
	def authenticate (self):
		print("### ENTER THE FOLLOWING URL IN A BROWSER AND AUTHORIZE THIS APPLICATION ###")
		print(self.api_url + "/oauth2/authenticate?client_id=" + self.client_id + "&redirect=" + self.redirect_url)
		print("### ONCE YOU HAVE AUTHORIZED THE APPLICATION, ENTER THE AUTH TOKEN HERE (WILL BE IN URL) ###")
		auth = input("Auth Token: ")
		self.auth_token = auth
		self.config['auth_token'] = self.auth_token
		# Make Request for Access Token
		r = requests.get(self.api_url + "/oauth2/access_token?secret=" + self.secret + "&code=" + self.auth_token)
		if(r.status_code == 200):
			# Success
			self.access_token = r.json()['result']['access_token']
			self.config['access_token'] = self.access_token
			self.save_config()
		elif(r.status_code == 400):
			# Authentication Error
			raise Exception("Authentication Error")
		else:
			# Other Error
			raise Exception("A strange error has occurred. Derp.")

	### Folder Methods ###

	## List Directory Contents
	def dir (self, path = ""):
		r = requests.get(self.api_url + "/folders/" + path + "?access_token=" + self.access_token)
		if(self.verbose):
			print("[Network] dir request: " + self.api_url + "/folders/" + path + "?access_token=" + self.access_token)
		if(r.status_code == 200):
			# Success
			contents = r.json()['result']['items']
			return contents
		elif(r.status_code == 400):
			# Folder Not Found
			raise Exception(r.json()['error']['code'], r.json()['error']['message'])
		else:
			# Other Error
			raise Exception("A strange error has occurred. Derp.")

	## Add Folder
	def mkdir (self, path, folder_name):
		payload = {'folder_name' : folder_name}
		r = requests.post(self.api_url + "/folders/" + path + "?access_token=" + self.access_token, data=payload)
		if(r.status_code == 200):
			# Make Sure Errors aren't here
			if(r.json()['error'] == None):
				# Check to see if this folder was Existing
				if(r.json()['result']['items'][0]['status'] == "existing"):
					raise Exception(409, "This folder already exists. Please choose another name and try again.")
				# Success
				return r.json()['result']['items'][0]
			else:
				if(r.json()['error']['code'] == 2022):
					raise Exception(2022, r.json()['error']['message'])
				elif(r.json()['error']['code'] == 2023):
					raise Exception(2023, r.json()['error']['message'])
				else:
					# Other Error
					raise Exception("A strange error has occurred. Derp.")
		else:
			if(r.json()['error'] != None):
				raise Exception(r.json['error']['code'], r.json['error']['message'])
			else:
				# Other Error
				raise Exception("A strange error has occurred. Derp.")

	## Remove Folder
	def rmdir(self, path):
		payload = {'path' : path}
		r = requests.delete(self.api_url + "/folders/?access_token=" + self.access_token, data=payload)
		if(r.status_code == 200):
			if(r.json()['error'] == None):
				# Success
				# @todo - If it doesn't delete anything (if not found) it will still return a success.
				return True
			else:
				if(r.json()['error']['code'] == 2022):
					raise Exception(2022, r.json()['error']['message'])
				elif(r.json()['error']['code'] == 2023):
					raise Exception(2023, r.json()['error']['message'])
				else:
					# Other Error
					raise Exception("A strange error has occurred. Derp.")
		else:
			if(r.json()['error'] != None):
				raise Exception(r.json()['error']['code'], r.json()['error']['message'])
			else:
				# Other Error
				raise Exception("A strange error has occurred. Derp.")

	## Rename Folder
	def renamedir(self, path, new_name):
		payload = {'from' : path, 'filename': new_name}
		r = requests.post(self.api_url + "/folders?operation=rename&access_token=" + self.access_token, data=payload)
		if(r.status_code == 200):
			if(r.json()['error'] == None):
				# Success
				# @todo - If it doesn't delete anything (if not found) it will still return a success.
				return True
			else:
				if(r.json()['error']['code'] == 2022):
					raise Exception(2022, r.json()['error']['message'])
				elif(r.json()['error']['code'] == 2023):
					raise Exception(2023, r.json()['error']['message'])
				else:
					# Other Error
					raise Exception("A strange error has occurred. Derp.")
		else:
			if(r.json()['error'] != None):
				raise Exception(r.json()['error']['code'], r.json()['error']['message'])
			else:
				# Other Error
				raise Exception("A strange error has occurred. Derp.")

	## Move Folder
	def mvdir(self, path, new_path):
		payload = {'from' : path, 'to': new_path}
		r = requests.post(self.api_url + "/folders?operation=move&access_token=" + self.access_token, data=payload)
		if(r.status_code == 200):
			if(r.json()['error'] == None):
				# Success
				# @todo - If it doesn't delete anything (if not found) it will still return a success.
				return True
			else:
				if(r.json()['error']['code'] == 2022):
					raise Exception(2022, r.json()['error']['message'])
				elif(r.json()['error']['code'] == 2023):
					raise Exception(2023, r.json()['error']['message'])
				else:
					# Other Error
					raise Exception("A strange error has occurred. Derp.")
		else:
			if(r.json()['error'] != None):
				raise Exception(r.json()['error']['code'], r.json()['error']['message'])
			else:
				# Other Error
				raise Exception("A strange error has occurred. Derp.")

	## Copy Folder
	def cpdir(self, path, new_path):
		payload = {'from' : path, 'to': new_path}
		r = requests.post(self.api_url + "/folders?operation=copy&access_token=" + self.access_token, data=payload)
		if(r.status_code == 200):
			if(r.json()['error'] == None):
				# Success
				# @todo - If it doesn't delete anything (if not found) it will still return a success.
				return True
			else:
				if(r.json()['error']['code'] == 2022):
					raise Exception(2022, r.json()['error']['message'])
				elif(r.json()['error']['code'] == 2023):
					raise Exception(2023, r.json()['error']['message'])
				else:
					# Other Error
					raise Exception("A strange error has occurred. Derp.")
		else:
			if(r.json()['error'] != None):
				raise Exception(r.json()['error']['code'], r.json()['error']['message'])
			else:
				# Other Error
				raise Exception("A strange error has occurred. Derp.")
	
	### File Methods ###

	## Download File
	def read(self, path, file_id, file_name, file_size, stream=False):
		return False
	
	## Upload File
	# Please Bitcasa, make Uploads better (eh I suppose it works, but it'd be nice to have pause/resume support via chunked requests)
	# Below is a memory efficient, multipart encoding beast.
	# @todo - Maybe add option to send File object directly
	# @todo - Fix content type detection
	def write(self, path, file_path):
		payload = BitcasaUploader(file_path, 8192)
		headers = {'Content-Type': payload.content_type, 'Content-Length': str(payload.totalsize)}
		print(path)
		r = requests.post(self.file_api_url + "/files"+path+"?access_token=" + self.access_token, data=payload, headers=headers);
		print(r.text)