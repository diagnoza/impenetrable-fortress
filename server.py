import socket
import threading
import logging
import json
import sys

# Configure logging to write to a file 'server_log.txt'
logging.basicConfig(
    filename='server_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, server):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server
        self.client_id = None

    def run(self):
        try:
            # Receive authentication data from the client
            auth_data = self.client_socket.recv(1024).decode()
            logging.info(f"Received authentication data from {self.client_address}: {auth_data}")
            data = json.loads(auth_data)

            # Hardcoded users dictionary
            users = self.server.users

            # Extract the client ID and password from the received data
            self.client_id = data.get("id")
            password = data.get("password")

            # If the client ID exists
            if self.client_id in users:
                # If the password matches, authenticate the user
                if users[self.client_id] == password:
                    self.client_socket.send(b"Authentication successful")
                    logging.info(f"Client {self.client_id} authenticated successfully.")
                else:
                    self.client_socket.send(b"Authentication failed: Incorrect password")
                    logging.warning(f"Incorrect password for client {self.client_id} from {self.client_address}.")
                    return  # Stop processing further if the password is incorrect
            else:
                # If the client ID does not exist, create a new user with the provided password
                users[self.client_id] = password
                self.client_socket.send(b"Authentication successful, new user created")
                logging.info(f"New user {self.client_id} created with provided password.")

            # Simulate some interaction with the client (e.g., processing actions)
            while True:
                action_data = self.client_socket.recv(1024).decode()
                if not action_data:
                    break  # Client closed connection

                logging.info(f"Received action data from {self.client_id}: {action_data}")
                response = f"Processed action: {action_data}"
                self.client_socket.send(response.encode())

        except Exception as e:
            logging.error(f"Error handling client {self.client_address}: {e}")
        finally:
            self.server.deregister_client(self.client_id)
            self.client_socket.close()
            logging.info(f"Connection closed with {self.client_address}")


class Server:
    def __init__(self, host="localhost", port=8080):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.users = {}  # Dictionary for storing users (client_id -> password)
        self.active_connections = 0
        self.lock = threading.Lock()

    def start(self):
        """Start the server and begin listening for incoming client connections."""
        try:
            # Enable address reuse to allow server restart without waiting for timeouts
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind the server to the specified host and port
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)  # Allow up to 5 pending connections
            logging.info(f"Server started on {self.host}:{self.port} and listening for connections...")

            while True:
                try:
                    # Wait for a client to connect
                    client_socket, client_address = self.server_socket.accept()
                    logging.info(f"Accepted connection from {client_address}")

                    # If the server is at capacity, reject the connection
                    if self.active_connections >= 3:
                        logging.warning(f"Max connections reached. Rejecting connection from {client_address}")
                        client_socket.send(b"Server is full. Try again later.")
                        client_socket.close()
                        continue

                    # Increment active connection count and start a new thread to handle the client
                    with self.lock:
                        self.active_connections += 1

                    client_handler = ClientHandler(client_socket, client_address, self)
                    client_handler.start()

                except Exception as e:
                    logging.error(f"Error while accepting connection: {e}")

        except OSError as e:
            logging.error(f"Failed to bind to port {self.port}: {e}")
            print(f"Port {self.port} is in use. Try a different port or terminate the conflicting process.")
            sys.exit(1)

    def register_client(self, client_id, client_handler):
        """Register a new client in the server."""
        with self.lock:
            self.clients[client_id] = client_handler
        logging.info(f"Registered client {client_id}.")

    def deregister_client(self, client_id):
        """Deregister a client from the server."""
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
            self.active_connections -= 1
        logging.info(f"Deregistered client {client_id}. Active connections: {self.active_connections}")


if __name__ == "__main__":
    server = Server()
    server.start()
