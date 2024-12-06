import socket
import json
import sys
import logging
import time

# Configure logging
logging.basicConfig(filename="client_log.txt",level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Client:
    def __init__(self, config_path, client_id):
        self.client_id = client_id
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.load_config(config_path)

    def load_config(self, config_path):
        """Load configuration for the client."""
        try:
            with open(config_path, 'r') as file:
                config_list = json.load(file)
                config = next((c for c in config_list if c["id"] == self.client_id), None)
                if not config:
                    raise ValueError(f"No configuration found for client ID '{self.client_id}'")
                self.id = config["id"]
                self.password = config["password"]
                self.server_ip = config["server"]["ip"]
                self.server_port = int(config["server"]["port"])
                self.actions = config["actions"]["steps"]
                self.delay = int(config["actions"]["delay"])
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            raise

    def connect(self):
        """Establish connection with the server."""
        try:
            self.client_socket.connect((self.server_ip, self.server_port))
            logging.info("Connected to server.")
        except socket.error as e:
            logging.error(f"Connection error: {e}")
            sys.exit(1)

    def authenticate(self):
        """Authenticate with the server."""
        auth_data = json.dumps({"id": self.id, "password": self.password})
        self.client_socket.send(auth_data.encode())
        logging.info(f"Sent authentication data: {auth_data}")

        response = self.client_socket.recv(1024).decode()
        logging.info(f"Received response from server: {response}")
        if "Authentication Failed" in response:
            logging.error("Authentication failed. Disconnecting.")
            self.disconnect()
            sys.exit(1)

    def send_actions(self):
        """Send action steps to the server."""
        action_data = json.dumps({"actions": {"delay": self.delay, "steps": self.actions}})
        self.client_socket.send(action_data.encode())
        logging.info(f"Sent action data to server: {action_data}")
        response = self.client_socket.recv(1024).decode()
        logging.info(f"Server response: {response}")

    def listen_for_server(self):
        """Listen for server responses and handle disconnection."""
        try:
            while True:
                response = self.client_socket.recv(1024)
                if not response:
                    logging.info("Disconnected by server.")
                    break
                time.sleep(1)
        except (socket.error, ConnectionResetError):
            logging.warning("Connection closed by server.")
        finally:
            self.disconnect()

    def disconnect(self):
        """Close the client socket."""
        self.client_socket.close()
        logging.info("Disconnected from server.")

    def run(self):
        """Run the client workflow."""
        try:
            self.connect()
            self.authenticate()
            self.send_actions()
            logging.info("Client is now idle. Press Ctrl+C to disconnect.")
            self.listen_for_server()
        except KeyboardInterrupt:
            logging.info("Client interrupted by user.")
            self.disconnect()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            self.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.error("Usage: python client.py <client_id>")
        sys.exit(1)

    client_id = sys.argv[1]
    try:
        client = Client("client_config.json", client_id)
        client.run()
    except ValueError as ve:
        logging.error(ve)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
