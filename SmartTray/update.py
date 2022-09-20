Version = "Cam-v1.20"
import os, uos, network, usocket, ussl, sensor, image, machine, time, gc, pyb, tf, senko, urequests
from mqtt import MQTTClient
OTA = senko.Senko(user="SeahorseRTHK", repo="Seahorse", working_dir="SmartTray", files=["update.py"])
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.UXGA)
sensor.skip_frames(time = 2000)
PORT = 443
HOST = "notify-api.line.me"
token = "MPkSNSnyyyxkeUqaGrcHZxtG6LNTj5vazBJmhtYshew"
SSID="Seahorse"
KEY="789456123"
currentTime = "dd/mm//yy hh:mm"
print("Trying to connect... (may take a while)...")
wlan = network.WINC()
try:
	wlan.connect(SSID, key=KEY, security=wlan.WPA_PSK)
	print(wlan.ifconfig())
except OSError:
	try:
		print("Failed to connect to WiFi, trying again after 3 seconds")
		time.sleep_ms(3000)
		wlan.connect(SSID, key=KEY, security=wlan.WPA_PSK)
		print(wlan.ifconfig())
	except:
		machine.reset()
except:
	print("Failed again, restarting")
	machine.reset()
try:
	addr = usocket.getaddrinfo(HOST, PORT)[0][-1]
	print(addr)
except OSError:
	try:
		addr = usocket.getaddrinfo(HOST, PORT)[0][-1]
		print(addr)
	except:
		machine.reset()
except:
	machine.reset()
try:
	print("Reading file")
	f = open("camInfo.txt", "r")
	temp = f.read(4)
	message = f.read()
	f.close()
	print("message is " + message)
except OSError:
	print("OSError 2 ENOENT = file/dir does not exist, creating file")
	f = open("camInfo.txt", "w")
	f.write("cam:no-setting-is-available")
	message = "cam:no-setting-is-available"
	print("Created new camInfo.txt file with cam:no-setting-is-available")
	f.close()
mainTopic = message
MQTT = MQTTClient(mainTopic, "vps.seahorse.asia", port=1883, keepalive=60000)
try:
	print("Connecting to MQTT server")
	MQTT.connect()
	print("Connected to MQTT server")
except OSError:
	try:
		print("Failed to connect to MQTT server, trying again after 3 seconds")
		time.sleep_ms(3000)
		MQTT.connect()
		print("Connected to MQTT server")
	except:
		machine.reset()
except:
	print("doing machine reset")
	machine.reset()
def callback(topic, msg):
	print(topic, msg)
	if msg == b'photo':
		message = mainTopic + " " + Version + ", photo"
		sendLINEphoto(message, None, None)
	elif b'photow,' in msg:
		msg = msg.decode("utf-8")
		text = msg.split(",",1)
		print("text[0] is", (text[0]))
		print("text[1] is", (text[1]))
		message = mainTopic + " " + Version + ", photo " + text[1]
		sendLINEphoto(message, None, text[1])
	elif msg == b'details':
		f = open("camInfo.txt", "r")
		temp = f.read(4)
		info = f.read()
		f.close()
		message = info + "-" + Version + ". IP: " + wlan.ifconfig()[0] + ". RSSI: " + str(wlan.rssi())
		sendLINEmsg(message)
	elif msg == b'grayscale':
		sensor.set_pixformat(sensor.GRAYSCALE)
		message = "Camera set to grayscale"
		sendLINEmsg(message)
	elif msg == b'rgb565':
		sensor.set_pixformat(sensor.RGB565)
		message = "Camera set to RGB565"
		sendLINEmsg(message)
	elif msg == b'lineimage' or msg == b'linephoto':
		message = mainTopic + " " + Version + ", photo"
		sendLINEphoto(message, None, None)
	elif msg == b'mqttimage' or msg == b'mqttphoto':
		sensor.set_framesize(sensor.QVGA)
		sensor.set_windowing(240,240)
		img = sensor.snapshot().compress(quality=75)
		MQTT.publish(mainTopic+"/Photo", img)
		del img
	elif msg == b'update':
		print("Updating")
		sendLINEmsg("Attempting update")
		try:
			if OTA.update():
				sendLINEmsg("Update complete! Arranging files")
				print("Update complete! Arranging files")
				os.rename("/main.py","/backup/backup.py")
				os.rename("/update.py","/main.py")
				print("Files arranged, restarting")
				time.sleep_ms(1000)
				machine.reset()
		except:
			sendLINEmsg("Failed to update")
			print("Not updated!")
	elif msg == b'restart':
		print("Restarting")
		MQTT.publish(mainTopic + "/state", "Restarting")
		sendLINEmsg("Command received, restarting")
		machine.reset()
	elif msg == b'reset':
		print("Reseting")
		MQTT.publish(mainTopic + "/state", "Reseting")
		sendLINEmsg(mainTopic + " is reseting")
		f = open("camInfo.txt", "w")
		f.write("cam:no-setting-is-available")
		f.close()
		machine.reset()
	elif msg == b'detectfeed':
		print("Detecting feed")
		detectFeed()
	elif msg == b'collectdata':
		count = 1
		while count <= 50:
			sendLINEmsg("Taking a picture in 5 seconds")
			time.sleep_ms(5000)
			message = "Photo no." + str(count)
			sendLINEphoto(message, None, None)
			time.sleep_ms(67000)
			count = count + 1
	elif msg == b'help':
		message = "commands:\ndetails\ngrayscale\nrgb565\nlineimage OR linephoto OR photo\nmqttimage OR mqttphoto\nphotow,(TEXT HERE)\ndetectfeed\ncollectdata\nupdate\nrestart\nhelp"
		sendLINEmsg(message)
	else:
		message = "Received invalid command: " + msg.decode('UTF-8') + ". Send command help to get help"
		sendLINEmsg(message)
MQTT.set_callback(callback)
MQTT.subscribe(mainTopic)
MQTT.set_last_will(mainTopic + "/state", "OFFLINE")
def sendLINEmsg(msg):
	LINE_Notify = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
	LINE_Notify.connect(addr)
	LINE_Notify.settimeout(5.0)
	LINE_Notify = ussl.wrap_socket(LINE_Notify, server_hostname=HOST)
	head = "--Taiwan\r\nContent-Disposition: form-data; name=\"message\"; \r\n\r\n" + msg
	tail = "\r\n--Taiwan--\r\n"
	totalLen = str(len(head) + len(tail))
	request = "POST /api/notify HTTP/1.1\r\n"
	request += "cache-control: no-cache\r\n"
	request += "Authorization: Bearer " + token + "\r\n"
	request += "Content-Type: multipart/form-data; boundary=Taiwan\r\n"
	request += "User-Agent: Honwis\r\n"
	request += "Accept: */*\r\n"
	request += "HOST: " + HOST + "\r\n"
	request += "accept-encoding: gzip, deflate\r\n"
	request += "Connection: close\r\n"
	request += "Content-Length: " + totalLen + "\r\n"
	request += "\r\n"
	LINE_Notify.write(request)
	LINE_Notify.write(head)
	LINE_Notify.write(tail)
	print(LINE_Notify.read())
	gc.collect()
	LINE_Notify.close()
def sendLINEphoto(msg,img,text):
	LINE_Notify = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
	LINE_Notify.connect(addr)
	LINE_Notify.settimeout(5.0)
	LINE_Notify = ussl.wrap_socket(LINE_Notify, server_hostname=HOST)
	if msg is None:
		message = mainTopic
	else:
		message = msg
	if img is None:
		sensor.set_framesize(sensor.UXGA)
		sensor.set_windowing(1600,1200)
		img = sensor.snapshot()
		if text is not None:
			x = img.width() - 95
			y = img.height() - 30
			r = 255
			g = 0
			b = 0
			img.draw_string(x, y, text, color = (r, g, b), scale = 10, mono_space = False,
								char_rotation = 0, char_hmirror = False, char_vflip = False,
								string_rotation = -90, string_hmirror = False, string_vflip = False)
		img.compress(quality=95)
	else:
		if text is not None:
			x = img.width() - 95
			y = img.height() - 30
			r = 255
			g = 0
			b = 0
			img.draw_string(x, y, text, color = (r, g, b), scale = 10, mono_space = False,
								char_rotation = 0, char_hmirror = False, char_vflip = False,
								string_rotation = -90, string_hmirror = False, string_vflip = False)
		img.compress(quality=95)
	head = "--Taiwan\r\nContent-Disposition: form-data; name=\"message\"; \r\n\r\n" + message + "\r\n--Taiwan\r\nContent-Disposition: form-data; name=\"imageFile\"; filename=\"" + mainTopic + ".jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
	tail = "\r\n--Taiwan--\r\n"
	totalLen = str(len(head) + len(tail) + len(img.bytearray()))
	print("totalLen is " + totalLen)
	request = "POST /api/notify HTTP/1.1\r\n"
	request += "cache-control: no-cache\r\n"
	request += "Authorization: Bearer " + token + "\r\n"
	request += "Content-Type: multipart/form-data; boundary=Taiwan\r\n"
	request += "User-Agent: Honwis\r\n"
	request += "Accept: */*\r\n"
	request += "HOST: " + HOST + "\r\n"
	request += "accept-encoding: gzip, deflate\r\n"
	request += "Connection: close\r\n"
	request += "Content-Length: " + totalLen + "\r\n"
	request += "\r\n"
	LINE_Notify.write(request)
	LINE_Notify.write(head)
	LINE_Notify.write(img.bytearray())
	LINE_Notify.write(tail)
	del img
	gc.collect()
	print(LINE_Notify.read())
	print("")
	LINE_Notify.close()
def detectFeed():
	sensor.set_framesize(sensor.UXGA)
	img = sensor.snapshot()
	sendLINEphoto("Detecting feed:", img, None)
	MQTT.publish("86Box/Photo/Raw", img.compress(quality=90))
	gc.collect()
MQTT.publish(mainTopic + "/state", "ONLINE")
sendLINEmsg(mainTopic + " " + Version + " is online" + ". IP: " + wlan.ifconfig()[0] + ". RSSI: " + str(wlan.rssi()))
time.sleep_ms(500)
f = open("camInfo.txt", "r")
temp = f.read(4)
message = f.read()
f.close()
print("temp is " + temp)
print("message is " + message)
if temp == "cam:":
	if (temp+message) == "cam:no-setting-is-available":
		print("Preparing camera to read QR codes")
		sensor.set_pixformat(sensor.GRAYSCALE)
		sensor.set_framesize(sensor.VGA)
		sensor.skip_frames(time = 2000)
		sensor.set_auto_gain(False)
		sendLINEmsg("Camera ready to read QR code")
		time.sleep_ms(2000)
		print("No setting, scanning for QR code")
		while (temp+message) == "cam:no-setting-is-available":
			img = sensor.snapshot()
			img.lens_corr(1.8)
			for code in img.find_qrcodes():
				img.draw_rectangle(code.rect(), color = (255, 0, 0))
				print(code)
				read = code.payload()
				print("code.payload is " + read)
				sendLINEmsg("QR code scanned: " + read + ". Restarting device with new settings")
				f = open("camInfo.txt", "w")
				f.write(read)
				f.close()
				print("Set, restarting")
				machine.reset()
			del img
			time.sleep_ms(100)
	else:
		info = message.split("-")
		print(info)
		print(len(info))
		for x in info:
			print(x)
else:
	sendLINEmsg("Setting is " + temp + message + ". Wrong setting, please set again. Restarting")
	f = open("camInfo.txt", "w")
	f.write("cam:no-setting-is-available")
	f.close()
	machine.reset()
net = None
labels = None
try:
	os.mkdir("/backup")
except:
	print("Already exist")
try:
	net = tf.load("trained.tflite", load_to_fb=uos.stat('trained.tflite')[6] > (gc.mem_free() - (64*1024)))
except Exception as e:
	print(e)
	raise Exception('Failed to load "trained.tflite", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')
try:
	labels = [line.rstrip('\n') for line in open("labels.txt")]
except Exception as e:
	raise Exception('Failed to load "labels.txt", did you copy the .tflite and labels.txt file onto the mass-storage device? (' + str(e) + ')')
start = pyb.millis()
while True:
	if (wlan.isconnected() == True):
		if pyb.elapsed_millis(start) == 1500:
			try:
				print("waiting")
				MQTT.check_msg()
				start = pyb.millis()
			except:
				print("No message")
				start = pyb.millis()
				try:
					MQTT.publish(mainTopic + "/state", "Waiting for command")
				except:
					machine.reset()
	else:
		machine.reset()