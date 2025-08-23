import time
from logic.download_mission import main

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Ошибка: {e}")
        print("Перезапуск через 10 секунд...")
        time.sleep(10)
