import os
import time
import subprocess
import requests
import logging
from dotenv import load_dotenv


class ProcessMonitor:
    def __init__(self, bot_token, chat_id):
        self.TELEGRAM_BOT_TOKEN = bot_token
        self.TELEGRAM_CHAT_ID = chat_id

    def telegram_bot_sendtext(self, message):
        """
        Send a Telegram message with the provided text.
        """
        try:
            send_text = (
                f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}"
                f"/sendMessage?chat_id={self.TELEGRAM_CHAT_ID}&text={message}"
            )
            response = requests.get(send_text)
            if response.status_code != 200:
                logging.error(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")

    def is_process_running(self, script_name):
        """
        Check if a process with the given script name is running.
        """
        try:
            # Run `ps aux` to get a list of all processes
            result = subprocess.run(
                ["ps", "aux"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Look for the script name in the process list
            for line in result.stdout.splitlines():
                if script_name in line and "python" in line:
                    return True
            return False
        except Exception as e:
            logging.error(f"Error checking process: {e}")
            return False

    def monitor_processes(self, scripts_to_monitor):
        """
        Continuously monitor the specified processes.
        """
        while True:
            all_running = True
            for script_name in scripts_to_monitor:
                if not self.is_process_running(script_name):
                    all_running = False
                    alert_message = f"Alert: Process {script_name} is not running!"
                    logging.warning(alert_message)
                    print(f"{time.ctime()}: {alert_message}")
                    self.telegram_bot_sendtext(alert_message)
                    break  # Avoid multiple alerts in the same hour
            
            if not all_running:
                logging.info(f"{time.ctime()}: Sleeping for 1 hour before re-checking.")
                time.sleep(3600)  # Sleep for 1 hour
            else:
                logging.info(f"{time.ctime()}: All processes are running.")
                print(f"{time.ctime()}: All processes are running.")
                time.sleep(60)  # Sleep for 1 minute if all processes are fine


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    SCRIPTS_TO_MONITOR = [
        "main_dividend.py",
        "option_research.py"
    ]

    logging.basicConfig(
        filename='status_checker.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.info("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in the environment.")
        exit(1)

    monitor = ProcessMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    monitor.monitor_processes(SCRIPTS_TO_MONITOR)
