"""Launch actual saved Ask conversations without API keys, model downloads or a GPU."""
from local_services import demo_environment, launch_services, require_frontend


def main():
    npm = require_frontend(8000, 5173)
    env = demo_environment(VITE_REPLAY_ONLY="1")
    launch_services(npm, "medrag.api.replay_app:app", 8000, 5173, env)


if __name__ == "__main__":
    main()
