import socket, json, time, sys

class Client:
    def __init__(self, config_path, client_id):
        self.client_id = client_id
        self.load_config(config_path)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def load_config(self, config_path):
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

    def connect_to_server(self):
        self.client_socket.connect((self.server_ip, self.server_port))
        print("Connected to server")

        auth_data = json.dumps({
            "id": self.id,
            "password": self.password
        })
        self.client_socket.send(auth_data.encode())
        response = self.client_socket.recv(1024).decode()
        print("Server response:", response)

        action_data = json.dumps({
            "actions": {
                "delay": self.delay,
                "steps": self.actions
            }
        })
        self.client_socket.send(action_data.encode())
        response = self.client_socket.recv(1024).decode()
        print("Server response:", response)

        print("Client is now idle. Press Ctrl+C to disconnect.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.disconnect()

    def disconnect(self):
        self.client_socket.close()
        print("Disconnected from server")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python client_conc.py <client_id>")
        sys.exit(1)

    client_id = sys.argv[1]
    client = Client("client_config.json", client_id)
    client.connect_to_server()

