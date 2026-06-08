INSERT INTO users (name, email, email_hash, nickname, nickname_hash, dni, dni_hash, password, global_role, stripe_customer_id, created_at, updated_at)
VALUES  ('gAAAAABqIcXbY9ymbrxBF8GzbW710XZU-anpipAqMdNdupK7hpdnLgSJeo5gg_zqkeYIPlSrPuNpucHgn7YQ5Cih7fTeAtgQ1A==', 'gAAAAABqIcXbbIEEmjjhL4fl7Rbo7Gn1PhIIGjL0uSg7OfMgIoqS22kvwcRpKURG3z7nJlBkRxZYrINMoU9_x_i0TFKwAXl1lA==', '51806ae91bbbd9e77fd42d439dc5eadbc4b2113926a21d0b9e008690682736d6', 'gAAAAABqIcXbljSchVQ6XmsumsWPZsDDDH8xpkHzX3VWuQElDpZO1S5LcH2gO_t2Mzetrb8N6qkPgJQlELkDaZZRQPvS2vNIhg==', 'c1c224b03cd9bc7b6a86d77f5dace40191766c485cd55dc48caf9ac873335d6f', 'gAAAAABqJu6_kb1HStbRlN0A668zrncX3w4Z9muSpmwdAVCLwd_ZcQ_eAsXzykL0uds-H3f161J9TRHtR7JCtj6-eR54CCSyGA==', 'e0cfc93ef472b6eb57227b299ca55532b7c5e0d229cf552cb8cb7ae1f230a99a', 'gAAAAABqIcXbiqQia5X-57PTGbaw8WFCMfGa86stG2YYKgQFIr_8WwAGPu93hQ6-kwuQDqQX08waNGwtaFqFa4FF1Q92rbYnow==', 'Admin', NULL, '2026-06-04 18:37:15.90212', NULL);

INSERT INTO institutions (name) VALUES
('UBA');

INSERT INTO profiles (name, questions_create_limit) VALUES
('basic_uba_user', 150);