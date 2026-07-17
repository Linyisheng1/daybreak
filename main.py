import uvicorn

from app import create_app
from config import WORKSPACE, get_config, load_config
from logger import setup_logging


def _run_encoding_self_test() -> None:
    from core.conversation.compaction import _encoding_for_model

    encoding = _encoding_for_model("gpt-4")
    if encoding is None:
        raise RuntimeError("cl100k_base encoding is unavailable")
    token_count = len(encoding.encode("Daybreak encoding self-test"))
    if token_count <= 0:
        raise RuntimeError("cl100k_base encoding returned no tokens")
    print(f"encoding self-test passed: cl100k_base ({token_count} tokens)")


def main() -> None:
    cfg = get_config()
    application = create_app()
    uvicorn.run(
        application,
        host=cfg.system.listen_addr,
        port=cfg.system.listen_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--self-test-encoding"]:
        _run_encoding_self_test()
        raise SystemExit(0)

    load_config()
    setup_logging(level="INFO", file_path=WORKSPACE / "app.log")

    main()
