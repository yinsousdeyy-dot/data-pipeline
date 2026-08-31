
        CREATE TABLE IF NOT EXISTS fct_orders (
            order_id VARCHAR(64) PRIMARY KEY,
            customer_id INT NOT NULL,
            customer_email VARCHAR(255) NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            status VARCHAR(20) NOT NULL,
            order_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            loaded_at TIMESTAMP WIdfsTH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_fct_orders_customer ON fct_orders(customer_id);

        