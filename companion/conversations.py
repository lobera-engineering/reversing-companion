"""Persist real model replies from Hermes' database, independently of tool budget."""
import sqlite3

from . import core as c


def persist_response(item, *, capture_snapshot=True):
    database = c.workdir() / 'hermes/state.db'
    if not database.is_file():
        return None
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        session = db.execute('SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1').fetchone()
        if not session:
            return None
        row = db.execute("SELECT id,session_id,content FROM messages WHERE session_id=? AND role='assistant' "
                         "AND COALESCE(tool_calls,'') IN ('','[]','null') AND length(content)>=400 "
                         'ORDER BY id DESC LIMIT 1', (session['id'],)).fetchone()
    if not row:
        return None
    # Keep the model's words verbatim. This is an answer artifact, not a claim
    # that the model has completed or correctly solved the entire chapter.
    path = c.workdir() / 'conversations' / f'{row["session_id"]}-{row["id"]}.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(row['content'] + '\n')
        c.record(item, text='Hermes response (not independently certified): ' + str(path))
    review = c.workdir() / 'agent-review.md'
    if not review.is_file() or review.stat().st_size < 200:
        review.write_text(row['content'] + '\n')
    result = {'path': str(path), 'session_id': row['session_id'], 'message_id': row['id'],
              'lesson': item['id'], 'at': c.now(), 'scope': 'Saved model response, not article certification'}
    if capture_snapshot:
        try:
            state = c.session()
            if state['lesson'] == item['id']:
                result['snapshot'] = str(c.snapshot())
        except (RuntimeError, OSError) as exc:
            result['snapshot_error'] = str(exc)
    c.write_json(c.workdir() / 'last-response.json', result)
    return result
