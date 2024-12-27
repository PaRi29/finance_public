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
        send_text = "https://api.telegram.org/bot" + self.TELEGRAM_BOT_TOKEN + \
            "/sendMessage?chat_id=" + self.TELEGRAM_CHAT_ID + \
            "&text={}".format(str(message))
        requests.get(send_text)

    def is_process_running(self, process_name):
        """
        Check if a process with the given name is running.
        """
        try:
            result = subprocess.run(
                ["pgrep", "-fl", process_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return process_name in result.stdout
        except Exception as e:
            logging.info(f"Error checking process: {e}")
            return False

    def monitor_processes(self, processes_to_monitor):
        """
        Continuously monitor the specified processes.
        """
        while True:
            all_running = True
            for process_name in processes_to_monitor:
                if not self.is_process_running(process_name):
                    all_running = False
                    alert_message = f"Alert: Process {process_name} is not running!"
                    logging.info(f"{time.ctime()}: {alert_message}")
                    self.telegram_bot_sendtext(alert_message)
                    break  # Exit the loop to avoid multiple alerts in the same hour
            
            if not all_running:
                logging.info(f"{time.ctime()}: Sleeping for 1 hour before re-checking.")
                time.sleep(3600)  # Sleep for 1 hour
            else:
                logging.info(f"{time.ctime()}: All processes are running.")
                time.sleep(60)  # Sleep for 1 minute if all processes are fine


if __name__ == "__main__":
    # Replace with your Telegram bot token and chat ID
    load_dotenv()

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    PROCESSES_TO_MONITOR = ["main_dividend.py", "main_short.py"]

    logging.basicConfig(filename='status_checker.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    monitor = ProcessMonitor(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    monitor.monitor_processes(PROCESSES_TO_MONITOR)
