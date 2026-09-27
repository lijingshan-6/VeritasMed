"""Launch the source-bound audit panel, independently of retrieval or GPU services."""
from local_services import demo_environment, launch_services, require_frontend


def main():
    npm = require_frontend(8001, 5174)
    env = demo_environment(VITE_API_URL="http://127.0.0.1:8001", VITE_AUDIT_ONLY="1")
    launch_services(npm, "medrag.api.audit_app:app", 8001, 5174, env, "/audit")


if __name__ == "__main__":
    main()
