from nova.core import memoria


def test_memoria_init_and_save(tmp_path):
    # override db path
    memoria_path = tmp_path / "nova_memory.db"
    memoria_db = str(memoria_path)
    from config import settings as cfg

    cfg.settings.db_path = memoria_db

    memoria.init_db()
    memoria.save_conversation("s1", "user", "hola", "dolphin-mistral:7b", "reason")
    memoria.save_conversation(
        "s1", "assistant", "respuesta", "dolphin-mistral:7b", "reason"
    )
    conv = memoria.get_conversation("s1")
    assert len(conv) >= 2
