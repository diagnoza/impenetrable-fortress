import socket, threading, json, logging

logging.basicConfig(
    filename='server_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ClientHandler(threading.Thread):
    def __init__(self, client_socket, address, server):
        super().__init__()
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.client_id = None
        self.password = None

    def authenticate(self, data):
        self.client_id = data.get("id")
        self.password = data.get("password")

        if self.client_id in self.server.users:
            if self.server.users[self.client_id]['password'] != self.password:
                return False, "Incorrect password for the provided ID"
        else:
            self.server.users[self.client_id] = {
                'password': self.password,
                'counter': 0,
                'connections': 0
            }
            logging.info(f"New user registered: {self.client_id}")

        return True, "Authentication successful"

    def run(self):
        try:
            data = json.loads(self.client_socket.recv(1024).decode())
            success, message = self.authenticate(data)

            if not success:
                self.client_socket.send(f"Authentication Failed: {message}".encode())
                logging.warning(f"Authentication failed for user {self.client_id}: {message}")
                return

            self.server.register_client(self.client_id, self)
            self.server.users[self.client_id]['connections'] += 1
            logging.info(f"User {self.client_id} connected from {self.address}")
            self.client_socket.send(b"Registration Successful")

            while True:
                action_data = self.client_socket.recv(1024).decode()
                if not action_data:
                    break
                actions = json.loads(action_data).get("actions", {}).get("steps", [])
                delay = int(json.loads(action_data).get("actions", {}).get("delay", 1))
                for action in actions:
                    threading.Event().wait(delay)
                    self.process_action(action)

                self.client_socket.send(b"Actions Processed")

        except Exception as e:
            logging.error(f"Error handling client {self.address}: {e}")
        finally:
            if success:
                self.server.users[self.client_id]['connections'] -= 1
                self.server.deregister_client(self.client_id)
            self.client_socket.close()

    def process_action(self, action):
        try:
            action_type, amount = action.split()
            amount = int(amount)

            if action_type == "INCREASE":
                self.server.users[self.client_id]['counter'] += amount
            elif action_type == "DECREASE":
                self.server.users[self.client_id]['counter'] -= amount

            new_value = self.server.users[self.client_id]['counter']
            logging.info(f"Client {self.client_id} - Action: {action_type} {amount}, New Counter: {new_value}")
        except ValueError:
            logging.error(f"Invalid action format received from {self.client_id}: {action}")

class Server:
    def __init__(self, host="localhost", port=8080):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.users = {}

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        logging.info("Server started and listening on port %s", self.port)

        while True:
            client_socket, address = self.server_socket.accept()
            logging.info(f"Accepted connection from {address}")
            client_handler = ClientHandler(client_socket, address, self)
            client_handler.start()

    def register_client(self, client_id, client_handler):
        self.clients[client_id] = client_handler
        logging.info(f"Registered client {client_id}")

    def deregister_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
            logging.info(f"Client {client_id} connection closed")

        if client_id in self.users and self.users[client_id]['connections'] == 0:
            logging.info(f"Removing data for user {client_id} as no active connections remain")
            del self.users[client_id]

if __name__ == "__main__":
    server = Server()
    server.start()

