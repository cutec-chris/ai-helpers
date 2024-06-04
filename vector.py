import mdsplit,sqlite3,sqlite_vss,datetime
db = None
max_length = 300
def split(text):
    for part in mdsplit.split_by_heading(text,3):
        embed_source = ''.join(part.text)
        while '\n\n' in embed_source: embed_source = embed_source.replace('\n\n','\n')
        while len(embed_source)>max_length:
            yield embed_source[:max_length]
            embed_source = embed_source[max_length:]
        yield embed_source
def init(path=None):
    global db
    if not path:
        db = sqlite3.connect(':memory:')    
    else:
        db = sqlite3.connect(path)
    db.enable_load_extension(True)
    sqlite_vss.load(db)
    db.execute("""
        create table if not exists knowledge (
            type TEXT,
            content TEXT,
            url TEXT,
            timestamp timestamp,
            content_embedding TEXT
        );
    """)
    db.execute("""
        create virtual table if not exists vss_knowledge using vss0(content_embedding(512));
    """)
def add(type,content,url,content_embedding):
    global db
    res = db.execute("""
    INSERT INTO knowledge (type, content,url, timestamp, content_embedding) VALUES (?, ?, ?, ?, ?);
    """,[type,content,url,datetime.datetime.now(),content_embedding])
    db.execute("""
    INSERT INTO vss_knowledge(rowid, content_embedding) VALUES (?, ?)
    """,[res.lastrowid, content_embedding])
def search(type,content):
    global db
    res = db.execute("""
        with matches as (
                select rowid,
                distance
                from vss_knowledge where vss_search(content_embedding, (?))
                limit 10
                )
        select
            knowledge.type,
            knowledge.command,
            knowledge.content,
            knowledge.timestamp,
            matches.distance
        from matches left join knowledge on knowledge.rowid = matches.rowid
    """)
    return res
def has_url(url):
    pass