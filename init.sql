-- init.sql：把 learn 库恢复成「刚建好表」的状态。
-- 用法：psql -U postgres -h 127.0.0.1 -d learn -f init.sql
-- 注意：每次执行都会清空这两张表的数据，上线后不能这么用。

DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 外键不会自动建索引：没有这一行，「查某个用户的笔记」会全表扫描
CREATE INDEX idx_notes_user_id ON notes (user_id);
