from interfaces.gpio_manager import GPIOManager

def run_web_app():
    from web_admin import create_app
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)

def main():
    # 🔴 FIRST THING THAT RUNS
    GPIOManager.init()

    from threading import Thread
    Thread(target=run_web_app, daemon=True).start()

    from ui.app import BankApp
    BankApp().run()

if __name__ == "__main__":
    main()
