import socket
import threading
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"client_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
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

def start_client():
    """Start the client to connect to server on port 443 and forward to another host on port 5432."""
    try:
        # Connect to server on port 443
        client_443 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_443.connect(('localhost', 443))
        logger.info("Connected to server on port 443")

        # Connect to target host on port 5432
        target_5432 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_5432.connect(('localhost', 5432))  # Replace 'localhost' with target host if different
        logger.info("Connected to target host on port 5432")

        # Start forwarding data in both directions
        threading.Thread(target=forward_data, args=(client_443, target_5432), daemon=True).start()
        threading.Thread(target=forward_data, args=(target_5432, client_443), daemon=True).start()

        # Keep the main thread running
        while True:
            pass
    except Exception as e:
        logger.error(f"Client error: {e}")
    finally:
        try:
            client_443.close()
            target_5432.close()
        except:
            pass

if __name__ == "__main__":
    start_client()
