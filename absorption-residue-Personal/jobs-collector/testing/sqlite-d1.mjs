// Offline D1-shaped adapter using real SQLite through Python (already required by CI).
import {spawnSync} from 'node:child_process';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const script = `
import json, sqlite3, sys
request=json.load(sys.stdin)
db=sqlite3.connect(sys.argv[1])
db.row_factory=sqlite3.Row
db.execute('PRAGMA foreign_keys=ON')
def execute(statement):
    before=db.total_changes
    cursor=db.execute(statement['sql'], statement['args'])
    rows=[dict(row) for row in cursor.fetchall()] if cursor.description else []
    return {'results':rows, 'success':True, 'meta':{'changes':db.total_changes-before}}
try:
    with db:
        results=[execute(statement) for statement in request]
    print(json.dumps(results))
finally:
    db.close()
`;

export class SQLiteD1 {
  constructor() {
    this.directory = mkdtempSync(join(tmpdir(), 'collector-test-'));
    this.path = join(this.directory, 'jobs.sqlite3');
  }
  execute(statements) {
    const result = spawnSync('python', ['-c', script, this.path], {
      input: JSON.stringify(statements.map(({sql, args}) => ({sql, args}))), encoding: 'utf8'
    });
    if (result.status !== 0) throw new Error(result.stderr || result.error?.message || 'SQLite adapter failed');
    return JSON.parse(result.stdout);
  }
  prepare(sql) {
    const database = this;
    return {
      sql, args: [],
      bind(...args) { return Object.assign(database.prepare(sql), {args}); },
      async run() { return database.execute([this])[0]; },
      async all() { return this.run(); },
      async first(column) {
        const row = (await this.all()).results[0] || null;
        return column && row ? row[column] : row;
      }
    };
  }
  async batch(statements) { return this.execute(statements); }
  close() { rmSync(this.directory, {recursive: true, force: true}); }
}
