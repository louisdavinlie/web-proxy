import sys
import socket
from threading import Thread, Lock, active_count
from mimetypes import guess_type
from urllib.parse import urlparse

ATTACKED_MSG = b"""
HTTP/1.1 200 OK
Content-Type: text/html

<html><body><h1>You are being attacked</h1></body></html>
"""

BAD_REQUEST = b"""
HTTP/1.1 400 Bad Request
Content-Type: text/html

<html><head><title>400 Bad Request</title></head><body><center><h1>400 Bad Request</h1></center><hr><center>nginx/1.18.0 (Ubuntu)</center></body></html>
"""

TELEMETRY = {}

def main(port: int, img_sub: int, atk_mode: int):
	# Create proxy connection
	in_sock = create_incoming_sock(port=port)

	# Accept client connections
	accept_client_conns(in_sock=in_sock, img_sub=img_sub, atk_mode=atk_mode)


def create_incoming_sock(*, port: int) -> socket.socket:
	# Create connection
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.bind(('', port))
		sock.settimeout(10)
		sock.listen()
		print(f"Server started on port {port}.")
		return sock
	except Exception as e:
		print("Server failed to start.")
		print(e)
		sys.exit(2)
	

def accept_client_conns(*, in_sock: socket.socket, img_sub: int, atk_mode: int):
	lock = Lock()

	while True:
		try:
			cl_conn, cl_addr = in_sock.accept()
			data = cl_conn.recv(8192)
			parsed_data = parse_data(data)
			if not parsed_data:
				continue
			t = Thread(target=send_to_server, args=(cl_conn, data, img_sub, atk_mode, parsed_data, lock))
			t.start()
		except socket.timeout:
			if active_count() == 1 and TELEMETRY:
				for k, v in TELEMETRY.items():
					print(f"{k}, {v}")
				TELEMETRY.clear()
			continue
		except KeyboardInterrupt:
			in_sock.close()
			print("Force closed.")
			sys.exit(1)

def send_to_server(cl_conn: socket.socket, data: bytes, img_sub: int, atk_mode: int, parsed_data: dict, lock: Lock):
	
	if not data.startswith(b"GET"):
		return

	if not parsed_data:
		cl_conn.send(BAD_REQUEST)
		cl_conn.close()
		return

	if img_sub and parsed_data and parsed_data["url"]:
		url_type = guess_type(parsed_data["url"])[0]
		if url_type and url_type.startswith("image"):
			data_split = data.split(b" ")
			data_split[1] = b"http://ocna0.d2.comp.nus.edu.sg:50000/change.jpg"
			data = b" ".join(data_split)

	# Create socket to server
	out_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	out_sock.connect(parsed_data["sr_addr"])
	out_sock.settimeout(5)
	out_sock.sendall(data)

	referer = parsed_data["referer"]
	url = parsed_data["url"]
	telemetry_key = referer if referer else url
	lock.acquire()
	try:
		if atk_mode:
			cl_conn.send(ATTACKED_MSG)
			TELEMETRY.setdefault(telemetry_key, 0)
			TELEMETRY[telemetry_key] += sys.getsizeof(ATTACKED_MSG.strip().split(b"\n\n")[1])
		else:
			while True:
				reply = out_sock.recv(8192)
				if len(reply) <= 0:
					break
				cl_conn.send(reply)
				
				if not reply.startswith(b"HTTP/1.1 200 OK") and not reply.startswith(b"HTTP/1.0 200 OK"):
					continue
				
				content_length = get_content_length(reply)
				if not content_length:
					split_reply = reply.split(b"\r\n\r\n")
					content_length = sys.getsizeof(split_reply[1]) if len(split_reply) > 1 else 0
				TELEMETRY.setdefault(telemetry_key, 0)
				TELEMETRY[telemetry_key] += content_length

		lock.release()
		cl_conn.close()
		out_sock.close()
	
	except socket.timeout:
		lock.release()
		cl_conn.close()
		out_sock.close()
		

def parse_data(data: bytes):
	decoded = data
	decoded_split = [string.split(b" ") for string in decoded.split(b"\n")]
	decoded_dict = {arr[0]: arr for arr in decoded_split}
	first_line = decoded_dict.get(b"GET")

	if not first_line:
		return None

	url = first_line[1].decode()
	
	parsed_url = urlparse(url)

	hostname = parsed_url.hostname
	port = parsed_url.port if parsed_url.port else 80
	referer = None
	if b"Referer:" in decoded_dict:
		referer = decoded_dict[b"Referer:"][1].decode().strip('\r')

	return {"sr_addr": (hostname, port), "url": url, "referer": referer}

def get_content_length(data: bytes):
	decoded = data
	decoded_split = [string.split(b" ") for string in decoded.split(b"\n")]
	decoded_dict = {arr[0]: arr for arr in decoded_split}
	if b"Content-Length:" in decoded_dict:
		return int(decoded_dict[b"Content-Length:"][1].decode().strip('\r'))
	else:
		return 0

if __name__ == "__main__":
	port = int(sys.argv[1])
	img_sub = int(sys.argv[2])
	atk_mode = int(sys.argv[3])
	main(port, img_sub, atk_mode) 