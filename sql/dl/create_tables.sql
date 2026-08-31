

create table if not exists fct_orders(
  order_id varchar(64) primary key,
  customer_id int not null,
  customer_email varchar(255) not null,
  amount numberic(10,2) not null,
  status varchar(20) not null,
  order_timestamp timestamp with time zone not null,
  loadded_at timestamp with time zone default CURRENT_TIMESTAMP
);

CREATE INDEX IF NO EXISTS idx_fct_orders_customer ON fct_orders(customer_id);
