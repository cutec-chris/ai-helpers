import mdsplit,sqlite3,sqlite_vss
db = None
def split(text):
    return mdsplit.split_by_heading(text,1)
def init(path=None):
    global db
    if not path:
        db = sqlite3.connect(':memory:')    
    else:
        db = sqlite3.connect(path)
    db.enable_load_extension(True)
    sqlite_vss.load(db)
    db.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            type TEXT,
            content TEXT,
            url TEXT,
            timestamp TEXT,
            message_embedding TEXT
        );
    """)
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vss_knowledge using vss0(message_embedding(512));
    """)