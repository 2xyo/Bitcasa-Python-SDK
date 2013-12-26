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