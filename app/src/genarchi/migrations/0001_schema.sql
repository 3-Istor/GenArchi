-- Schéma initial de la billetterie (contracts/domain/model.md).
CREATE TABLE IF NOT EXISTS events (
    id             text PRIMARY KEY,
    name           text NOT NULL,
    venue          text NOT NULL,
    starts_at      timestamptz NOT NULL,
    sales_open_at  timestamptz NOT NULL,
    capacity       integer NOT NULL CHECK (capacity > 0),
    remaining      integer NOT NULL CHECK (remaining >= 0 AND remaining <= capacity),  -- I1
    price_cents    integer NOT NULL CHECK (price_cents >= 0),
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id               text PRIMARY KEY,
    event_id         text NOT NULL REFERENCES events(id),
    buyer_email      text NOT NULL,
    quantity         integer NOT NULL CHECK (quantity BETWEEN 1 AND 4),
    amount_cents     integer NOT NULL,
    idempotency_key  text NOT NULL,
    request_hash     text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, idempotency_key)                                                  -- I2
);

CREATE TABLE IF NOT EXISTS tickets (
    id          text PRIMARY KEY,
    order_id    text NOT NULL REFERENCES orders(id),
    event_id    text NOT NULL REFERENCES events(id),
    status      text NOT NULL CHECK (status IN ('pending', 'issued', 'scanned')),
    qr_object   text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    issued_at   timestamptz,
    scanned_at  timestamptz
);

CREATE INDEX IF NOT EXISTS tickets_order_idx ON tickets (order_id);
CREATE INDEX IF NOT EXISTS tickets_event_status_idx ON tickets (event_id, status);
CREATE INDEX IF NOT EXISTS tickets_pending_idx ON tickets (created_at) WHERE status = 'pending';
