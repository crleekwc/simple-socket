import socket
import threading
import select
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"server_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def forward_data(source, destination):
    """Forward data from source socket to destination socket, keeping connection alive."""
    source_addr = f"{source.getpeername()[0]}:{source.getpeername()[1]}"
    dest_addr = f"{destination.getpeername()[0]}:{destination.getpeername()[1]}"
    while True:
        try:
            data = source.recv(1024)
            if data:
                destination.sendall(data)
                logger.info(f"Forwarded {len(data)} bytes from {source_addr} to {dest_addr}")
            else:
                # No data received, but connection might still be alive; do not close
                continue
        except Exception as e:
            logger.error(f"Error forwarding data from {source_addr} to {dest_addr}: {e}")
            # Only break on specific errors indicating connection closure
            if isinstance(e, (ConnectionResetError, BrokenPipeError)):
                logger.info(f"Connection closed between {source_addr} and {dest_addr}")
                break
            continue
    # Do not close sockets to keep connection alive
    logger.info(f"Stopped forwarding between {source_addr} and {dest_addr}, but connections remain open")

def handle_client(client_5432, server_443):
    """Handle data transfer between client on 5432 and server on 443."""
    # This function is no longer used as pairing is handled in start_server
    pass

def start_server():
    """Start the server to listen on ports 5432 and 443."""
    # Create socket for port 5432
    server_5432 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_5432.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_5432.bind(('localhost', 5432))
    server_5432.listen(5)
    logger.info("Server listening on port 5432...")

    # Create socket for port 443
    server_443 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_443.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_443.bind(('localhost', 443))
        server_443.listen(5)
        logger.info("Server listening on port 443...")
    except Exception as e:
        logger.error(f"Failed to bind to port 443: {e}. This port may require elevated privileges.")
        return

    sockets = [server_5432, server_443]
    clients_5432 = []
    clients_443 = []

    try:
        while True:
            readable, _, _ = select.select(sockets, [], [])
            for sock in readable:
                if sock == server_5432:
                    client_5432, addr = server_5432.accept()
                    logger.info(f"Accepted connection from {addr} on port 5432")
                    clients_5432.append(client_5432)
                    if clients_443:
                        client_443 = clients_443.pop(0)
                        threading.Thread(target=forward_data, args=(client_5432, client_443), daemon=True).start()
                        threading.Thread(target=forward_data, args=(client_443, client_5432), daemon=True).start()
                elif sock == server_443:
                    client_443, addr = server_443.accept()
                    logger.info(f"Accepted connection from {addr} on port 443")
                    clients_443.append(client_443)
                    if clients_5432:
                        client_5432 = clients_5432.pop(0)
                        threading.Thread(target=forward_data, args=(client_5432, client_443), daemon=True).start()
                        threading.Thread(target=forward_data, args=(client_443, client_5432), daemon=True).start()
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        server_5432.close()
        server_443.close()

if __name__ == "__main__":
    start_server()
